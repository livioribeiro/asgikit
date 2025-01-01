import asyncio
import mimetypes
import os
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from email.utils import formatdate
from enum import StrEnum
from http import HTTPStatus
from http.cookies import SimpleCookie
from os import PathLike
from typing import Any

import aiofiles
import aiofiles.os

from asgikit._json import JSON_ENCODER
from asgikit.asgi import AsgiScope, AsgiReceive, AsgiSend
from asgikit.constants import (
    SCOPE_ASGIKIT,
    SCOPE_RESPONSE,
    SCOPE_RESPONSE_CONTENT_LENGTH,
    SCOPE_RESPONSE_CONTENT_TYPE,
    SCOPE_RESPONSE_COOKIES,
    SCOPE_RESPONSE_ENCODING,
    SCOPE_RESPONSE_HEADERS,
    SCOPE_RESPONSE_IS_FINISHED,
    SCOPE_RESPONSE_IS_STARTED,
    SCOPE_RESPONSE_STATUS,
)
from asgikit.errors.http import (
    ClientDisconnectError,
    ResponseNotStartedError,
    ResponseAlreadyEndedError,
    ResponseAlreadyStartedError
)
from asgikit.headers import MutableHeaders

__all__ = (
    "SameSitePolicy",
    "Response",
    "respond_text",
    "respond_status",
    "respond_redirect",
    "respond_redirect_post_get",
    "respond_json",
    "respond_stream",
    "respond_file",
    "stream_writer",
)


class SameSitePolicy(StrEnum):
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"


class Response:
    """Represents the response associated with a request

    Responses are created with their associated requests and can be written to
    """

    ENCODING = "utf-8"

    __slots__ = ("_scope", "_receive", "_send")

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        scope.setdefault(SCOPE_ASGIKIT, {})
        scope[SCOPE_ASGIKIT].setdefault(SCOPE_RESPONSE, {})

        scope[SCOPE_ASGIKIT][SCOPE_RESPONSE].setdefault(
            SCOPE_RESPONSE_STATUS, HTTPStatus.OK
        )
        scope[SCOPE_ASGIKIT][SCOPE_RESPONSE].setdefault(
            SCOPE_RESPONSE_HEADERS, MutableHeaders()
        )
        scope[SCOPE_ASGIKIT][SCOPE_RESPONSE].setdefault(
            SCOPE_RESPONSE_COOKIES, SimpleCookie()
        )
        scope[SCOPE_ASGIKIT][SCOPE_RESPONSE].setdefault(
            SCOPE_RESPONSE_ENCODING, self.ENCODING
        )
        scope[SCOPE_ASGIKIT][SCOPE_RESPONSE].setdefault(
            SCOPE_RESPONSE_IS_STARTED, False
        )
        scope[SCOPE_ASGIKIT][SCOPE_RESPONSE].setdefault(
            SCOPE_RESPONSE_IS_FINISHED, False
        )

        self._scope = scope
        self._receive = receive
        self._send = send

    @property
    def status(self) -> HTTPStatus | None:
        return self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_STATUS]

    @status.setter
    def status(self, status: HTTPStatus):
        self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_STATUS] = status

    @property
    def headers(self) -> MutableHeaders:
        return self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_HEADERS]

    @property
    def cookies(self) -> SimpleCookie:
        return self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_COOKIES]

    @property
    def content_type(self) -> str | None:
        return self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE].get(
            SCOPE_RESPONSE_CONTENT_TYPE
        )

    @content_type.setter
    def content_type(self, value: str):
        self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][
            SCOPE_RESPONSE_CONTENT_TYPE
        ] = value

    @property
    def content_length(self) -> int | None:
        return self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE].get(
            SCOPE_RESPONSE_CONTENT_LENGTH
        )

    @content_length.setter
    def content_length(self, value: str):
        self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_CONTENT_LENGTH] = value

    @property
    def encoding(self) -> str:
        return self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_ENCODING]

    @encoding.setter
    def encoding(self, value: str):
        self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_ENCODING] = value

    @property
    def is_started(self) -> bool:
        """Tells whether the response is started or not"""

        return self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_IS_STARTED]

    def __set_started(self):
        self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][SCOPE_RESPONSE_IS_STARTED] = True

    @property
    def is_finished(self) -> bool:
        """Tells whether the response is started or not"""

        return self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][
            SCOPE_RESPONSE_IS_FINISHED
        ]

    def __set_finished(self):
        self._scope[SCOPE_ASGIKIT][SCOPE_RESPONSE][
            SCOPE_RESPONSE_IS_FINISHED
        ] = True

    def header(self, name: str, value: str):
        self.headers.set(name, value)

    def cookie(
        self,
        name: str,
        value: str,
        *,
        expires: int = None,
        domain: str = None,
        path: str = None,
        max_age: int = None,
        secure: bool = False,
        httponly: bool = True,
        samesite: SameSitePolicy = SameSitePolicy.LAX,
    ):
        """Add a cookie to the response"""

        self.cookies[name] = value
        if expires is not None:
            self.cookies[name]["expires"] = expires
        if domain is not None:
            self.cookies[name]["domain"] = domain
        if path is not None:
            self.cookies[name]["path"] = path
        if max_age is not None:
            self.cookies[name]["max-age"] = max_age

        self.cookies[name]["secure"] = secure
        self.cookies[name]["httponly"] = httponly
        self.cookies[name]["samesite"] = samesite.value

    def __build_headers(self) -> list[tuple[bytes, bytes]]:
        if self.content_type is not None:
            if self.content_type.startswith("text/"):
                content_type = f"{self.content_type}; charset={self.encoding}"
            else:
                content_type = self.content_type

            self.header("content-type", content_type)

        if self.content_length is not None:
            self.header("content-length", str(self.content_length))

        return self.headers.encode()

    async def start(self):
        """Start the response

        Must be called before writing to the response
        :raise ResponseAlreadyStartedError: If the response is already started
        :raise ResponseAlreadyFinnishedError: If the response is finished
        """
        if self.is_started:
            raise ResponseAlreadyStartedError()

        if self.is_finished:
            raise ResponseAlreadyEndedError()

        self.__set_started()

        status = self.status
        headers = self.__build_headers()

        await self._send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": headers,
            }
        )

    async def write(self, data: bytes | str, *, more_body=False):
        """Write data to the response

        :raise ResponseNotStartedError: If the response is not started
        """

        encoded_data = data if isinstance(data, bytes) else data.encode(self.encoding)

        if not self.is_started:
            raise ResponseNotStartedError()

        await self._send(
            {
                "type": "http.response.body",
                "body": encoded_data,
                "more_body": more_body,
            }
        )

        if not more_body:
            self.__set_finished()

    async def end(self):
        """Finish the response

        Must be called when no more data will be written to the response
        :raise ResponseNotStartedError: If the response is not started
        :raise ResponseAlreadyFinnishedError: If the response is already finished
        """
        if not self.is_started:
            raise ResponseNotStartedError()

        if self.is_finished:
            raise ResponseAlreadyEndedError

        await self.write(b"", more_body=False)


async def respond_text(response: Response, content: str | bytes):
    """Respond with the given content and finish the response"""

    if isinstance(content, str):
        data = content.encode(response.encoding)
    else:
        data = content

    if not response.content_type:
        response.content_type = "text/plain"

    response.content_length = len(data)

    await response.start()
    await response.write(data, more_body=False)


async def respond_status(response: Response, status: HTTPStatus):
    """Respond with the given status and finish the response"""

    response.status = status
    await response.start()
    await response.end()


async def respond_redirect(response: Response, location: str, permanent: bool = False):
    """Respond with a redirect

    :param response: The response to write to
    :param location: Location to redirect to
    :param permanent: If true, send permanent redirect (HTTP 308),
    otherwise send a temporary redirect (HTTP 307).
    """

    status = (
        HTTPStatus.TEMPORARY_REDIRECT
        if not permanent
        else HTTPStatus.PERMANENT_REDIRECT
    )

    response.header("location", location)
    await respond_status(response, status)


async def respond_redirect_post_get(response: Response, location: str):
    """Response with HTTP status 303

    Used to send a redirect to a GET endpoint after a POST request, known as post-get redirect
    """

    response.header("location", location)
    await respond_status(response, HTTPStatus.SEE_OTHER)


async def respond_json(response: Response, content: Any):
    """Respond with the given content serialized as JSON"""

    data = JSON_ENCODER(content)
    if isinstance(data, str):
        data = data.encode(response.encoding)

    response.content_type = "application/json"
    await respond_text(response, data)


async def __listen_for_disconnect(receive):
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return


@asynccontextmanager
async def stream_writer(response: Response):
    """Context manager for streaming data to the response

    :raise ClientDisconnectError: If the client disconnects while sending data
    """

    await response.start()

    client_disconect = asyncio.create_task(
        __listen_for_disconnect(response._receive)
    )

    async def write(data: bytes | str):
        if client_disconect.done():
            raise ClientDisconnectError()
        await response.write(data, more_body=True)

    try:
        yield write
    finally:
        await response.end()
        client_disconect.cancel()


async def respond_stream(response: Response, stream: AsyncIterable[bytes | str]):
    """Respond with the given stream of data"""

    async with stream_writer(response) as write:
        async for chunk in stream:
            await write(chunk)


def __file_last_modified(stat: os.stat_result) -> str:
    return formatdate(stat.st_mtime, usegmt=True)


def __guess_mimetype(path: str | PathLike[str]) -> str | None:
    m_type, _ = mimetypes.guess_type(path, strict=False)
    return m_type


def __supports_pathsend(scope):
    return "extensions" in scope and "http.response.pathsend" in scope["extensions"]


def __supports_zerocopysend(scope):
    return "extensions" in scope and "http.response.zerocopysend" in scope["extensions"]


async def respond_file(response: Response, path: str | PathLike[str]):
    """Send the given file to the response"""

    if not response.content_type:
        response.content_type = __guess_mimetype(path)

    stat = await aiofiles.os.stat(path)
    content_length = stat.st_size
    last_modified = __file_last_modified(stat)

    response.content_length = content_length
    response.headers.set("last-modified", last_modified)

    if not isinstance(path, str):
        path = str(path)

    if __supports_pathsend(response._scope):
        await response.start()
        await response._send(
            {
                "type": "http.response.pathsend",
                "path": path,
            }
        )
        return

    if __supports_zerocopysend(response._scope):
        await response.start()
        file = await asyncio.to_thread(open, path, "rb")
        await response._send(
            {
                "type": "http.response.zerocopysend",
                "file": file.fileno(),
            }
        )
        return

    async with aiofiles.open(path, "rb") as stream:
        await respond_stream(response, stream)
