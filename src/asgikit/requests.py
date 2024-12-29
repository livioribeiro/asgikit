import asyncio
import re
from collections.abc import AsyncIterable, Awaitable, Callable
from http import HTTPMethod
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs, unquote_plus

from multipart import multipart

from asgikit._json import JSON_DECODER
from asgikit.asgi import AsgiProtocol, AsgiReceive, AsgiScope, AsgiSend
from asgikit.constants import (
    SCOPE_ASGIKIT,
    SCOPE_REQUEST,
    SCOPE_REQUEST_ATTRIBUTES,
    SCOPE_REQUEST_IS_CONSUMED,
)
from asgikit.errors.http import ClientDisconnectError
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


class Request:
    __slots__ = (
        "asgi",
        "_headers",
        "_query",
        "_cookie",
        "_charset",
        "response",
        "websocket",
    )

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        assert scope["type"] in ("http", "websocket")

        scope.setdefault(SCOPE_ASGIKIT, {})
        scope[SCOPE_ASGIKIT].setdefault(SCOPE_REQUEST, {})
        scope[SCOPE_ASGIKIT][SCOPE_REQUEST].setdefault(SCOPE_REQUEST_ATTRIBUTES, {})
        scope[SCOPE_ASGIKIT][SCOPE_REQUEST].setdefault(SCOPE_REQUEST_IS_CONSUMED, False)

        self.asgi = AsgiProtocol(scope, CallableProxy(receive), CallableProxy(send))

        self._headers: Headers | None = None
        self._query: Query | None = None
        self._charset = None
        self._cookie = None

        self.response = Response(*self.asgi) if self.is_http else None
        self.websocket = WebSocket(*self.asgi) if self.is_websocket else None

    @property
    def attributes(self) -> dict[str, Any]:
        return self.asgi.scope[SCOPE_ASGIKIT][SCOPE_REQUEST][SCOPE_REQUEST_ATTRIBUTES]

    @property
    def is_consumed(self) -> bool:
        return self.asgi.scope[SCOPE_ASGIKIT][SCOPE_REQUEST][SCOPE_REQUEST_IS_CONSUMED]

    def __set_consumed(self):
        self.asgi.scope[SCOPE_ASGIKIT][SCOPE_REQUEST][SCOPE_REQUEST_IS_CONSUMED] = True

    @property
    def is_http(self) -> bool:
        return self.asgi.scope["type"] == "http"

    @property
    def is_websocket(self) -> bool:
        return self.asgi.scope["type"] == "websocket"

    @property
    def http_version(self) -> str:
        return self.asgi.scope["http_version"]

    @property
    def server(self):
        return self.asgi.scope["server"]

    @property
    def client(self):
        return self.asgi.scope["client"]

    @property
    def scheme(self):
        return self.asgi.scope["scheme"]

    @property
    def method(self) -> HTTPMethod | None:
        """Return None when request is websocket"""

        if method := self.asgi.scope.get("method"):
            return HTTPMethod(method)

        return None

    @property
    def root_path(self):
        return self.asgi.scope["root_path"]

    @property
    def path(self):
        return self.asgi.scope["path"]

    @property
    def raw_path(self):
        return self.asgi.scope["raw_path"]

    @property
    def headers(self) -> Headers:
        if not self._headers:
            self._headers = Headers(self.asgi.scope["headers"])
        return self._headers

    @property
    def raw_query(self):
        return unquote_plus(self.asgi.scope["query_string"].decode("ascii"))

    @property
    def query(self) -> Query:
        if not self._query:
            self._query = Query(self.asgi.scope["query_string"])
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
    def accept(self):
        return self.headers.get_all("accept")

    def wrap_asgi(
        self,
        *,
        receive: Callable[[AsgiReceive], Awaitable] = None,
        send: Callable[[AsgiSend, dict], Awaitable] = None,
    ):
        if receive:
            self.asgi.receive.wrap(receive)

        if send:
            self.asgi.send.wrap(send)

    def __getitem__(self, item):
        return self.attributes[item]

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def __delitem__(self, key):
        del self.attributes[key]

    def __contains__(self, item):
        return item in self.attributes

    async def __aiter__(self) -> AsyncIterable[bytes]:
        if self.is_consumed:
            raise RuntimeError("request has already been consumed")

        self.__set_consumed()

        while True:
            message = await self.asgi.receive()

            if message["type"] == "http.request":
                yield message["body"]
                if not message["more_body"]:
                    break

            if message["type"] == "http.disconnect":
                raise ClientDisconnectError()


async def read_body(request: Request) -> bytes:
    body = bytearray()

    async for chunk in request:
        body.extend(chunk)

    return bytes(body)


async def read_text(request: Request, encoding: str = None) -> str:
    body = await read_body(request)
    return body.decode(encoding or request.charset)


async def read_json(request: Request) -> dict | list:
    body = await read_body(request)
    if not body:
        return {}

    return JSON_DECODER(body)


def _is_form_multipart(content_type: str) -> bool:
    return content_type.startswith(FORM_MULTIPART_CONTENT_TYPE)


async def read_form(request: Request) -> dict[str, str | multipart.File]:
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

    async for data in request:
        # `parser.write` can potentially write to a file,
        # therefore we need to call it using `asyncio.to_thread`
        await asyncio.to_thread(parser.write, data)

    return fields | files
