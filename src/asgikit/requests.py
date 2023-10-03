import asyncio
import json
import re
from collections.abc import AsyncIterable
from http import HTTPMethod
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs

from multipart import multipart

from asgikit.asgi import AsgiProtocol, AsgiReceive, AsgiScope, AsgiSend
from asgikit.errors.http import ClientDisconnectError
from asgikit.headers import Headers
from asgikit.query import Query
from asgikit.websockets import WebSocket

__all__ = (
    "Request",
    "read_body",
    "read_text",
    "read_json",
    "read_form",
    "_read_form_multipart",
)

FORM_URLENCODED_CONTENT_TYPE = "application/x-www-urlencoded"
FORM_MULTIPART_CONTENT_TYPE = "multipart/form-data"
FORM_CONTENT_TYPES = (FORM_URLENCODED_CONTENT_TYPE, FORM_MULTIPART_CONTENT_TYPE)

RE_CHARSET = re.compile(r"charset=([\w-]+)$")

ATTRIBUTES_KEY = "_attributes"


def _parse_cookie(data: str) -> dict[str, str]:
    cookie = SimpleCookie()
    cookie.load(data)
    return {key: value.value for key, value in cookie.items()}


class Request:
    __slots__ = (
        "_asgi",
        "_is_consumed",
        "_headers",
        "_query",
        "_cookie",
        "_charset",
        "_websocket",
    )

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        assert scope["type"] in ("http", "websocket")

        self._asgi = AsgiProtocol(scope, receive, send)

        if ATTRIBUTES_KEY not in scope:
            scope[ATTRIBUTES_KEY]: dict[str, Any] = {}

        self._is_consumed = False

        self._headers: Headers | None = None
        self._query: Query | None = None
        self._charset = None
        self._cookie = None

        self._websocket = WebSocket(self) if self.is_websocket else None

    @property
    def is_http(self) -> bool:
        return self._asgi.scope["type"] == "http"

    @property
    def is_websocket(self) -> bool:
        return self._asgi.scope["type"] == "websocket"

    @property
    def websocket(self) -> WebSocket | None:
        return self._websocket

    @property
    def http_version(self) -> str:
        return self._asgi.scope["http_version"]

    @property
    def server(self):
        return self._asgi.scope["server"]

    @property
    def client(self):
        return self._asgi.scope["client"]

    @property
    def scheme(self):
        return self._asgi.scope["scheme"]

    @property
    def method(self) -> HTTPMethod:
        return HTTPMethod(self._asgi.scope["method"])

    @property
    def root_path(self):
        return self._asgi.scope["root_path"]

    @property
    def path(self):
        return self._asgi.scope["path"]

    @property
    def raw_path(self):
        return self._asgi.scope["raw_path"]

    @property
    def headers(self) -> Headers:
        if not self._headers:
            self._headers = Headers(self._asgi.scope["headers"])
        return self._headers

    @property
    def query(self) -> Query:
        if not self._query:
            self._query = Query(self._asgi.scope["query_string"])
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

    @property
    def is_consumed(self) -> bool:
        return self._is_consumed

    @property
    def attributes(self) -> dict[str, Any]:
        return self._asgi.scope[ATTRIBUTES_KEY]

    def __getitem__(self, item):
        return self.attributes[item]

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def __delitem__(self, key):
        del self.attributes[key]

    def __contains__(self, item):
        return item in self.attributes

    async def __aiter__(self) -> AsyncIterable[bytes]:
        if self._is_consumed:
            raise RuntimeError("request has already been consumed")

        self._is_consumed = True

        while True:
            message = await self._asgi.receive()

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

    return json.loads(body)


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
