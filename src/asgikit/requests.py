import asyncio
import json
import re
from collections.abc import AsyncIterable
from enum import Enum
from functools import cache
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

from multipart import multipart

from asgikit.errors.http import ClientDisconnectError
from asgikit.http_connection import HttpConnection

RE_CHARSET = re.compile(r"charset=([\w-]+)$")


__all__ = (
    "HttpMethod",
    "HttpRequest",
    "read_body",
    "read_text",
    "read_json",
    "read_form",
    "_read_form_multipart",
)

FORM_URLENCODED_CONTENT_TYPE = "application/x-www-urlencoded"
FORM_MULTIPART_CONTENT_TYPE = "multipart/form-data"

FORM_CONTENT_TYPES = (FORM_URLENCODED_CONTENT_TYPE, FORM_MULTIPART_CONTENT_TYPE)


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
    return content_type.startswith(FORM_MULTIPART_CONTENT_TYPE)


class HttpRequest(HttpConnection):
    __slots__ = (
        "_is_consumed",
        "_cookie",
        "_charset",
    )

    def __init__(self, scope, receive, send):
        assert scope["type"] == "http"
        super().__init__(scope, receive, send)

        self._is_consumed = False
        self._cookie = None
        self._charset = None

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
    def charset(self) -> str:
        if not self._charset:
            values = RE_CHARSET.findall(self.content_type)
            self._charset = values[0] if values else "utf-8"
        return self._charset

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


async def read_text(request: HttpRequest, encoding: str = None) -> str:
    body = await read_body(request)
    return body.decode(encoding or request.charset)


async def read_json(request: HttpRequest) -> dict | list:
    body = await read_body(request)
    return json.loads(body)


async def read_form(request: HttpRequest) -> dict[str, str | multipart.File]:
    if "multipart/form-data" in request.content_type:
        return await _read_form_multipart(request)

    data = await read_text(request)

    return {
        k: v.pop() if len(v) == 1 else v
        for k, v in parse_qs(data, keep_blank_values=True).items()
    }


async def _read_form_multipart(
    request: HttpRequest,
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

    async for data in request.stream():
        # `parser.write` can potentially write to a file,
        # therefore we need to call it using `asyncio.to_thread`
        await asyncio.to_thread(parser.write, data)

    return fields | files
