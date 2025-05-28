import asyncio
import contextlib
import hashlib
import json
import logging
import mimetypes
import os
import re
from collections.abc import AsyncIterable, AsyncIterator
from email.utils import formatdate
from http import HTTPMethod, HTTPStatus
from typing import Any
from urllib.parse import parse_qs, unquote_plus

from asgikit.cookies import parse_cookie
from asgikit.errors.asgi import AsgiError
from asgikit.forms import UploadedFile

try:
    from asgikit import forms
except ImportError:
    forms = None

from asgikit._constants import (
    CHARSET,
    CONTENT_LENGTH,
    CONTENT_TYPE,
    COOKIES,
    DEFAULT_ENCODING,
    HEADERS,
    IS_CONSUMED,
    QUERY,
    REQUEST,
    SCOPE_ASGIKIT,
)
from asgikit.asgi import AsgiReceive, AsgiScope, AsgiSend
from asgikit.errors.form import MultipartBoundaryError, MultipartNotEnabledError
from asgikit.errors.http import ClientDisconnectError, RequestBodyAlreadyConsumedError
from asgikit.files import AsyncFile
from asgikit.headers import parse_headers
from asgikit.responses import Response
from asgikit.websockets import WebSocket

__all__ = ("Request",)

logger = logging.getLogger(__name__)

RE_CHARSET = re.compile(r"""charset="?([\w-]+)"?""")
RE_MULTIPART = re.compile(r"""boundary=\"?([\w-]+)\"?""")

FORM_URLENCODED_CONTENT_TYPE = "application/x-www-urlencoded"
FORM_MULTIPART_CONTENT_TYPE = "multipart/form-data"
FORM_CONTENT_TYPES = (FORM_URLENCODED_CONTENT_TYPE, FORM_MULTIPART_CONTENT_TYPE)


# pylint: disable=too-many-public-methods
class Request:
    """Represents the incoming request"""

    __slots__ = (
        "scope",
        "asgi_receive",
        "asgi_send",
        "response",
        "websocket",
    )

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        assert scope["type"] in ("http", "websocket")

        self.scope = scope
        self.asgi_receive = receive
        self.asgi_send = send

        if SCOPE_ASGIKIT not in scope:
            scope[SCOPE_ASGIKIT] = {}

        if REQUEST not in scope[SCOPE_ASGIKIT]:
            scope[SCOPE_ASGIKIT][REQUEST] = {}

        if IS_CONSUMED not in scope[SCOPE_ASGIKIT][REQUEST]:
            scope[SCOPE_ASGIKIT][REQUEST][IS_CONSUMED] = False

        self.response = (
            Response(self.scope, self.asgi_receive, self.asgi_send)
            if self.is_http
            else None
        )
        self.websocket = (
            WebSocket(self.scope, self.asgi_receive, self.asgi_send)
            if self.is_websocket
            else None
        )

    @property
    def is_http(self) -> bool:
        """Tell if the request is an HTTP request

        Returns False for websocket requests
        """

        return self.scope["type"] == "http"

    @property
    def is_websocket(self) -> bool:
        """Tell if the request is a WebSocket request

        Returns False for HTTP requests
        """

        return self.scope["type"] == "websocket"

    @property
    def http_version(self) -> str:
        return self.scope["http_version"]

    @property
    def server(self) -> tuple[str, int | None]:
        return self.scope["server"]

    @property
    def client(self) -> tuple[str, int] | None:
        return self.scope["client"]

    @property
    def scheme(self) -> str:
        return self.scope["scheme"]

    @property
    def method(self) -> HTTPMethod | None:
        """Return None when request is websocket"""

        if method := self.scope.get("method"):
            # pylint: disable=no-value-for-parameter
            return HTTPMethod(method)

        return None

    @property
    def root_path(self) -> str:
        return self.scope["root_path"]

    @property
    def path(self) -> str:
        return self.scope["path"]

    @property
    def raw_path(self) -> str | None:
        return self.scope["raw_path"]

    @property
    def headers(self) -> dict[str, str | list[str]]:
        if HEADERS not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            self.scope[SCOPE_ASGIKIT][REQUEST][HEADERS] = parse_headers(
                self.scope["headers"]
            )
        return self.scope[SCOPE_ASGIKIT][REQUEST][HEADERS]

    @property
    def raw_query(self) -> str:
        return unquote_plus(self.scope["query_string"].decode("ascii"))

    @property
    def query(self) -> dict[str, str]:
        if QUERY not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            query_string = self.scope["query_string"].decode("ascii")
            parsed_qs = parse_qs(query_string, keep_blank_values=True)
            self.scope[SCOPE_ASGIKIT][REQUEST][QUERY] = parsed_qs
        return self.scope[SCOPE_ASGIKIT][REQUEST][QUERY]

    @property
    def cookies(self) -> dict[str, str]:
        if COOKIES not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            if cookies := self.headers.get("cookie"):
                cookie_value = parse_cookie(cookies)
            else:
                cookie_value = {}
            self.scope[SCOPE_ASGIKIT][REQUEST][COOKIES] = cookie_value
        return self.scope[SCOPE_ASGIKIT][REQUEST][COOKIES]

    @property
    def content_type(self) -> str | None:
        if CONTENT_TYPE not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            if content_type := self.headers.get("content-type"):
                content_type = content_type.split(";")[0]
            else:
                content_type = None
            self.scope[SCOPE_ASGIKIT][REQUEST][CONTENT_TYPE] = content_type
        return self.scope[SCOPE_ASGIKIT][REQUEST][CONTENT_TYPE]

    @property
    def content_length(self) -> int | None:
        if CONTENT_LENGTH not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            if content_length := self.headers.get("content-length"):
                content_length = int(content_length)
            else:
                content_length = None
            self.scope[SCOPE_ASGIKIT][REQUEST][CONTENT_LENGTH] = content_length
        return self.scope[SCOPE_ASGIKIT][REQUEST].get(CONTENT_LENGTH)

    @property
    def charset(self) -> str | None:
        if CHARSET not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            if content_type := self.headers.get("content-type"):
                values = RE_CHARSET.findall(content_type)
                charset = values[0] if values else DEFAULT_ENCODING
            else:
                charset = DEFAULT_ENCODING
            self.scope[SCOPE_ASGIKIT][REQUEST][CHARSET] = charset
        return self.scope[SCOPE_ASGIKIT][REQUEST][CHARSET]

    @property
    def is_consumed(self) -> bool:
        """Verifies whether the request body is consumed or not"""
        return self.scope[SCOPE_ASGIKIT][REQUEST][IS_CONSUMED]

    def __set_consumed(self):
        self.scope[SCOPE_ASGIKIT][REQUEST][IS_CONSUMED] = True

    async def stream(self) -> AsyncIterator[bytes]:
        """iterate over the bytes of the request body

        :raise RequestBodyAlreadyConsumedError: If the request body is already consumed
        :raise ClientDisconnectError: If the client is disconnected while reading the request body
        """

        if self.is_consumed:
            raise RequestBodyAlreadyConsumedError()

        while True:
            message = await asyncio.wait_for(self.asgi_receive(), 1)

            if message["type"] == "http.request":
                data = message["body"]

                if not message["more_body"]:
                    self.__set_consumed()

                yield data

                if self.is_consumed:
                    break
            elif message["type"] == "http.disconnect":
                raise ClientDisconnectError()
            else:
                raise AsgiError(f"invalid message type: '{message['type']}'")

    async def read_bytes(self) -> bytes:
        """Read the full request body"""

        data = bytearray()

        async for chunk in self.stream():
            data.extend(chunk)

        return bytes(data)

    async def read_str(self, encoding: str = None) -> str:
        """Read the full request body as str"""

        data = await self.read_bytes()
        return data.decode(encoding or self.charset)

    async def read_json(self) -> Any:
        """Read the full request body and parse it as json"""

        if data := await self.read_bytes():
            return json.loads(data)

        return None

    @staticmethod
    def _is_form_multipart(content_type: str) -> bool:
        return content_type.startswith(FORM_MULTIPART_CONTENT_TYPE)

    async def read_form(
        self,
    ) -> dict[str, str | UploadedFile | list[str | UploadedFile]]:
        """Read the full request body and parse it as form encoded"""

        if self._is_form_multipart(self.content_type):
            if not forms:
                raise MultipartNotEnabledError()

            match = RE_MULTIPART.search(self.headers["content-type"])
            if not match:
                raise MultipartBoundaryError()

            boundary = match.group(1)
            return await forms.process_multipart(self.stream(), boundary)

        data = await self.read_str()
        if not data:
            return {}

        return {
            name: value[0] if len(value) == 1 else value
            for name, value in parse_qs(data, keep_blank_values=True).items()
        }

    async def respond_bytes(
        self,
        content: bytes,
        status=HTTPStatus.OK,
        media_type: str = None,
        headers: dict[str, str | list[str]] = None,
    ):
        """Respond with the given content and finish the response"""

        response = self.response

        response.status = status
        if media_type:
            response.media_type = media_type
        if headers:
            response.headers |= headers

        response.content_length = len(content)

        await response.start()
        await response.write(content, more_body=False)

    async def respond_text(
        self,
        content: str,
        status=HTTPStatus.OK,
        media_type: str = "text/plain",
        headers: dict[str, str | list[str]] = None,
    ):
        """Respond with the given content and finish the response"""

        data = content.encode(self.response.encoding)
        await self.respond_bytes(data, status, media_type, headers)

    async def respond_json(
        self,
        content: Any,
        status=HTTPStatus.OK,
        media_type: str = "application/json",
        headers: dict[str, str | list[str]] = None,
    ):
        """Respond with the given content serialized as JSON"""

        response = self.response

        data = json.dumps(
            content,
            allow_nan=False,
            indent=None,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        if isinstance(data, str):
            data = data.encode(response.encoding)

        await self.respond_bytes(data, status, media_type, headers)

    async def respond_status(
        self, status: HTTPStatus, headers: dict[str, str | list[str]] = None
    ):
        """Respond with the given status and finish the response"""

        response = self.response
        response.status = status

        if headers:
            response.headers |= headers

        await response.start()
        await response.end()

    async def redirect(
        self,
        location: str,
        permanent: bool = False,
        headers: dict[str, str | list[str]] = None,
    ):
        """Respond with a redirect

        :param location: Location to redirect to
        :param permanent: If true, send permanent redirect (HTTP 308),
        otherwise send a temporary redirect (HTTP 307).
        :param headers: Additional headers to include
        """

        status = (
            HTTPStatus.TEMPORARY_REDIRECT
            if not permanent
            else HTTPStatus.PERMANENT_REDIRECT
        )

        self.response.header("location", location)
        await self.respond_status(status, headers)

    async def redirect_post_get(
        self, location: str, headers: dict[str, str | list[str]] = None
    ):
        """Response with HTTP status 303

        Used to send a redirect to a GET endpoint after a POST request, known as post/redirect/get
        https://en.wikipedia.org/wiki/Post/Redirect/Get
        """

        self.response.header("location", location)
        await self.respond_status(HTTPStatus.SEE_OTHER, headers)

    async def __listen_for_disconnect(self):
        while True:
            try:
                message = await self.asgi_receive()
            except Exception:
                logger.exception("error while listening for client disconnect")
                break

            if message["type"] == "http.disconnect":
                break

    @contextlib.asynccontextmanager
    async def response_writer(
        self,
        status=HTTPStatus.OK,
        media_type: str = None,
        headers: dict[str, str | list[str]] = None,
    ):
        """Context manager for streaming data to the response

        :raise ClientDisconnectError: If the client disconnects while sending data
        """

        response = self.response
        response.status = status

        if media_type:
            response.media_type = media_type
        if headers:
            response.headers |= headers

        await response.start()

        client_disconect = asyncio.create_task(self.__listen_for_disconnect())

        async def write(data: bytes | str):
            if client_disconect.done():
                raise ClientDisconnectError()
            await response.write(data, more_body=True)

        try:
            yield write
        finally:
            await response.end()
            client_disconect.cancel()

    async def respond_stream(
        self,
        stream: AsyncIterable[bytes | str],
        status=HTTPStatus.OK,
        media_type: str = None,
        headers: dict[str, str | list[str]] = None,
    ):
        """Respond with the given stream of data

        :raise ClientDisconnectError: If the client disconnects while sending data
        """

        async with self.response_writer(status, media_type, headers) as write:
            async for chunk in stream:
                await write(chunk)

    async def respond_file(
        self,
        path: str | os.PathLike,
        status=HTTPStatus.OK,
        media_type: str = None,
        stat_result: os.stat_result = None,
    ):
        """Send the given file to the response"""

        response = self.response

        if status:
            response.status = status

        if media_type:
            response.media_type = media_type
        elif not response.media_type:
            m_type, _ = mimetypes.guess_type(path, strict=False)
            response.media_type = m_type

        if stat_result:
            response.content_length = stat_result.st_size
            last_modified = formatdate(stat_result.st_mtime, usegmt=True)
            etag_base = str(stat_result.st_mtime) + "-" + str(stat_result.st_size)
            etag = f'"{hashlib.md5(etag_base.encode(), usedforsecurity=False).hexdigest()}"'
            response.header("last-modified", last_modified)
            response.header("etag", etag)

        file = AsyncFile(path)
        if not response.content_length:
            stat = await file.stat()
            response.content_length = stat.st_size

        if "last-modified" not in response.headers:
            stat = await file.stat()
            last_modified = formatdate(stat.st_mtime, usegmt=True)
            response.headers["last-modified"] = [last_modified]

        if "http.response.pathsend" in self.scope.get("extensions", {}):
            await response.start()
            await self.asgi_send(
                {
                    "type": "http.response.pathsend",
                    "path": str(path),
                }
            )
            return

        if "http.response.zerocopysend" in self.scope.get("extensions", {}):
            await response.start()
            file = await asyncio.to_thread(open, path, "rb")
            await self.asgi_send(
                {
                    "type": "http.response.zerocopysend",
                    "file": file.fileno(),
                }
            )
            return

        try:
            async with file.stream() as stream:
                await self.respond_stream(stream)
        except ClientDisconnectError:
            pass
