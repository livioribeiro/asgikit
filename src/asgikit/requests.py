import asyncio
import json
from collections.abc import AsyncIterable
from enum import Enum
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

import multipart

from asgikit.errors.http import ClientDisconnectError
from asgikit.http import HttpConnection

__all__ = (
    "HttpMethod",
    "HttpRequest",
    "read_body",
    "read_text",
    "read_json",
    "read_form",
    "read_form_multipart",
)

FORM_CONTENT_TYPES = ("application/x-www-urlencoded", "multipart/form-data")


class HttpMethod(str, Enum):
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"

    def __str__(self):
        return self.value


def _parse_cookie(data: str) -> dict[str, str]:
    cookie = SimpleCookie()
    cookie.load(data)
    return {key: value.value for key, value in cookie.items()}


def _is_form(content_type: str) -> bool:
    return any(content_type.startswith(h) for h in FORM_CONTENT_TYPES)


def _is_form_multipart(content_type: str) -> bool:
    return FORM_CONTENT_TYPES[1] in content_type


class HttpRequest(HttpConnection):
    __slots__ = (
        "_is_consumed",
        "_cookie",
        "_body",
        "_text",
        "_json",
        "_form",
    )

    def __init__(self, scope, receive, send):
        assert scope["type"] == "http"
        super().__init__(scope, receive, send)

        self._is_consumed = False
        self._cookie = None
        self._body = None
        self._text = None
        self._json = None
        self._form = None

    @property
    def http_version(self) -> str:
        return self._context.scope["http_version"]

    @property
    def method(self) -> HttpMethod:
        return HttpMethod(self._context.scope["method"])

    @property
    def cookie(self) -> dict[str, str]:
        if not self._cookie and (cookie := self.headers.get_raw(b"cookie")):
            self._cookie = _parse_cookie(cookie.decode("latin-1"))
        return self._cookie

    @property
    def accept(self) -> list[str] | None:
        return self.headers.get_all("accept")

    @property
    def content_type(self) -> str | None:
        return self.headers.get("content-type")

    @property
    def content_length(self) -> int | None:
        if content_length := self.headers.get("content-length"):
            return int(content_length)
        return None

    @property
    def is_consumed(self) -> bool:
        return self._is_consumed

    async def stream(self) -> AsyncIterable[bytes]:
        if self._is_consumed:
            raise RuntimeError("request has already been consumed")

        self._is_consumed = True

        while True:
            message = await self._context.receive()
            if message["type"] == "http.request":
                yield message["body"]
                if not message["more_body"]:
                    break
            if message["type"] == "http.disconnect":
                raise ClientDisconnectError()


async def read_body(request: HttpRequest) -> bytes:
    body = bytearray()

    async for chunk in request.stream():
        body.extend(chunk)

    return bytes(body)


async def read_text(request: HttpRequest, encoding="utf-8") -> str:
    body = await read_body(request)
    return body.decode(encoding)


async def read_json(request: HttpRequest) -> dict | list:
    body = await read_body(request)
    return json.loads(body)


async def read_form(request: HttpRequest) -> dict[str, str]:
    data = await read_text(request)

    return {
        k: v.pop() if len(v) == 1 else v
        for k, v in parse_qs(data, keep_blank_values=True).items()
    }


async def read_form_multipart(
    request: HttpRequest,
) -> dict[str, str | multipart.multipart.File]:
    fields: dict[str, str] = {}
    files: dict[str, multipart.multipart.File] = {}

    def on_field(field: multipart.multipart.Field):
        fields[field.field_name.decode()] = field.value.decode()

    def on_file(file: multipart.multipart.File):
        files[file.field_name.decode()] = file

    parser = multipart.create_form_parser(request.headers, on_field, on_file)

    async for data in request.stream():
        await asyncio.to_thread(parser.write, data)

    return fields | files
