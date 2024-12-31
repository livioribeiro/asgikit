import asyncio
import re
from collections.abc import AsyncIterable
from http import HTTPMethod
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs, unquote_plus

from python_multipart import multipart

from asgikit._json import JSON_DECODER
from asgikit.asgi import AsgiReceive, AsgiScope, AsgiSend
from asgikit.constants import (
    SCOPE_ASGIKIT,
    SCOPE_REQUEST,
    SCOPE_REQUEST_ATTRIBUTES,
    SCOPE_REQUEST_IS_CONSUMED,
)
from asgikit.errors.http import ClientDisconnectError, RequestBodyAlreadyConsumedError
from asgikit.headers import Headers
from asgikit.query import Query
from asgikit.responses import Response
from asgikit.util.callable_proxy import CallableProxy
from asgikit.websockets import WebSocket

__all__ = (
    "Request",
    "read_body",
    "read_text",
    "read_json",
    "read_form",
)

FORM_URLENCODED_CONTENT_TYPE = "application/x-www-urlencoded"
FORM_MULTIPART_CONTENT_TYPE = "multipart/form-data"
FORM_CONTENT_TYPES = (FORM_URLENCODED_CONTENT_TYPE, FORM_MULTIPART_CONTENT_TYPE)

RE_CHARSET = re.compile(r"charset=([\w-]+)")


def _parse_cookie(data: str) -> dict[str, str]:
    cookie = SimpleCookie()
    cookie.load(data)
    return {key: value.value for key, value in cookie.items()}


class Body:
    """Async iterator over request body"""

    __slots__ = ("_scope", "_receive")

    def __init__(self, scope: AsgiScope, receive: AsgiReceive):
        self._scope = scope
        self._receive = receive

    @property
    def is_consumed(self) -> bool:
        """Verifies whether the request body is consumed or not"""
        return self._scope[SCOPE_ASGIKIT][SCOPE_REQUEST][SCOPE_REQUEST_IS_CONSUMED]

    def __set_consumed(self):
        self._scope[SCOPE_ASGIKIT][SCOPE_REQUEST][SCOPE_REQUEST_IS_CONSUMED] = True

    async def __aiter__(self) -> AsyncIterable[bytes]:
        """iterate over the bytes of the request body

        :raise RequestBodyAlreadyConsumedError: If the request body is already consumed
        :raise ClientDisconnectError: If the client is disconnected while reading the request body
        """

        if self.is_consumed:
            raise RequestBodyAlreadyConsumedError()

        self.__set_consumed()

        while True:
            message = await self._receive()

            if message["type"] == "http.request":
                yield message["body"]
                if not message["more_body"]:
                    break

            if message["type"] == "http.disconnect":
                raise ClientDisconnectError()


class Request:
    """Represents the incoming request"""

    __slots__ = (
        "_scope",
        "_receive",
        "_send",
        "_headers",
        "_query",
        "_cookie",
        "_charset",
        "body",
        "response",
        "websocket",
    )

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        assert scope["type"] in ("http", "websocket")

        scope.setdefault(SCOPE_ASGIKIT, {})
        scope[SCOPE_ASGIKIT].setdefault(SCOPE_REQUEST, {})
        scope[SCOPE_ASGIKIT][SCOPE_REQUEST].setdefault(SCOPE_REQUEST_ATTRIBUTES, {})
        scope[SCOPE_ASGIKIT][SCOPE_REQUEST].setdefault(SCOPE_REQUEST_IS_CONSUMED, False)

        self._scope = scope
        self._receive = CallableProxy(receive)
        self._send = CallableProxy(send)

        self._headers: Headers | None = None
        self._query: Query | None = None
        self._charset = None
        self._cookie = None

        self.body = Body(self._scope, self._receive)
        self.response = (
            Response(self._scope, self._receive, self._send)
            if self.is_http
            else None
        )
        self.websocket = (
            WebSocket(self._scope, self._receive, self._send)
            if self.is_websocket
            else None
        )

    @property
    def attributes(self) -> dict[str, Any]:
        """Request attributes in the scope of asgikit"""
        return self._scope[SCOPE_ASGIKIT][SCOPE_REQUEST][SCOPE_REQUEST_ATTRIBUTES]

    @property
    def is_http(self) -> bool:
        """Tell if the request is an HTTP request

        Returns False for websocket requests
        """
        return self._scope["type"] == "http"

    @property
    def is_websocket(self) -> bool:
        """Tell if the request is a WebSocket request

        Returns False for HTTP requests
        """
        return self._scope["type"] == "websocket"

    @property
    def http_version(self) -> str:
        return self._scope["http_version"]

    @property
    def server(self) -> tuple[str, int | None]:
        return self._scope["server"]

    @property
    def client(self) -> tuple[str, int] | None:
        return self._scope["client"]

    @property
    def scheme(self) -> str:
        return self._scope["scheme"]

    @property
    def method(self) -> HTTPMethod | None:
        """Return None when request is websocket"""

        if method := self._scope.get("method"):
            return HTTPMethod(method)

        return None

    @property
    def root_path(self) -> str:
        return self._scope["root_path"]

    @property
    def path(self) -> str:
        return self._scope["path"]

    @property
    def raw_path(self) -> str | None:
        return self._scope["raw_path"]

    @property
    def headers(self) -> Headers:
        if not self._headers:
            self._headers = Headers(self._scope["headers"])
        return self._headers

    @property
    def raw_query(self) -> str:
        return unquote_plus(self._scope["query_string"].decode("ascii"))

    @property
    def query(self) -> Query:
        if not self._query:
            self._query = Query(self._scope["query_string"])
        return self._query

    @property
    def cookie(self) -> dict[str, str]:
        if not self._cookie and (cookie := self.headers.get_raw(b"cookie")):
            self._cookie = _parse_cookie(cookie.decode("latin-1"))
        return self._cookie

    @property
    def content_type(self) -> str | None:
        return self.headers.get("content-type")

    @property
    def content_length(self) -> int | None:
        if content_length := self.headers.get("content-length"):
            return int(content_length)
        return None

    @property
    def charset(self) -> str:
        if not self._charset:
            values = RE_CHARSET.findall(self.content_type)
            self._charset = values[0] if values else "utf-8"
        return self._charset

    @property
    def accept(self) -> str:
        return self.headers["accept"]

    def wrap_asgi(
        self,
        *,
        receive: AsgiReceive = None,
        send: AsgiSend = None,
    ):
        if receive:
            self._receive.wrap(receive)

        if send:
            self._send.wrap(send)

    def __getitem__(self, item):
        return self.attributes[item]

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def __delitem__(self, key):
        del self.attributes[key]

    def __contains__(self, item):
        return item in self.attributes


async def read_body(request: Request) -> bytes:
    """Read the full request body"""

    body = bytearray()

    async for chunk in request.body:
        body.extend(chunk)

    return bytes(body)


async def read_text(request: Request, encoding: str = None) -> str:
    """Read the full request body as str"""

    body = await read_body(request)
    return body.decode(encoding or request.charset)


async def read_json(request: Request) -> dict | list:
    """Read the full request body and parse it as json"""

    body = await read_body(request)
    if not body:
        return {}

    return JSON_DECODER(body)


def _is_form_multipart(content_type: str) -> bool:
    return content_type.startswith(FORM_MULTIPART_CONTENT_TYPE)


async def read_form(request: Request) -> dict[str, str | multipart.File]:
    """Read the full request body and parse it as form encoded"""

    if _is_form_multipart(request.content_type):
        return await _read_form_multipart(request)

    data = await read_text(request)
    if not data:
        return {}

    return {
        k: v.pop() if len(v) == 1 else v
        for k, v in parse_qs(data, keep_blank_values=True).items()
    }


async def _read_form_multipart(
    request: Request,
) -> dict[str, str | multipart.File]:
    fields: dict[str, str] = {}
    files: dict[str, multipart.File] = {}

    charset = request.charset

    def on_field(field: multipart.Field):
        fields[field.field_name.decode(charset)] = field.value.decode(charset)

    def on_file(file: multipart.File):
        file.file_object.seek(0)
        files[file.field_name.decode(charset)] = file

    parser = multipart.create_form_parser(request.headers, on_field, on_file)

    async for data in request.body:
        # `parser.write` can potentially write to a file,
        # therefore we need to call it using `asyncio.to_thread`
        await asyncio.to_thread(parser.write, data)

    return fields | files
