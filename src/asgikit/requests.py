import json
import os
from collections.abc import AsyncIterable
from enum import Enum
from http.cookies import SimpleCookie
from typing import Optional
from urllib.parse import parse_qs

from asgikit.http_connection import HttpConnection
from asgikit.multipart.process import process_form

__all__ = ("HttpMethod", "HttpRequest")

FORM_MULTIPART_ENABLED = False
if enable_multipart := os.getenv("ASGIKIT_ENABLE_FORM_MULTIPART"):
    FORM_MULTIPART_ENABLED = enable_multipart in ("true", "True", "1")

if FORM_MULTIPART_ENABLED:
    FORM_CONTENT_TYPES = ("application/x-www-urlencoded", "multipart/form-data")
else:
    FORM_CONTENT_TYPES = ("application/x-www-urlencoded",)


class HttpMethod(Enum):
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
    return any(h in content_type for h in FORM_CONTENT_TYPES)


class HttpRequest(HttpConnection):
    __slots__ = (
        "http_version",
        "method",
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

        self.http_version = scope["http_version"]
        self.method = HttpMethod(scope["method"])

        self._is_consumed = False
        self._cookie = None
        self._body = None
        self._text = None
        self._json = None
        self._form = None

    @property
    def cookie(self) -> dict[str, str]:
        if not self._cookie and (cookie := self.headers.get_raw("cookie")):
            self._cookie = _parse_cookie(cookie.decode("latin-1"))
        return self._cookie

    @property
    def accept(self) -> Optional[list[str]]:
        return self.headers.get_all("accept")

    @property
    def content_type(self) -> Optional[str]:
        return self.headers.get("content-type")

    @property
    def content_length(self) -> Optional[int]:
        content_length = self.headers.get("content-length")
        if content_length is not None:
            return int(content_length)
        return None

    async def stream(self) -> AsyncIterable[bytes]:
        if self._body:
            yield self._body
            return

        if self._is_consumed:
            raise RuntimeError("request has already been consumed")

        self._is_consumed = True

        while True:
            message = await self.asgi_callbacks.receive()
            if message["type"] == "http.request":
                yield message["body"]
                if not message["more_body"]:
                    break
            if message["type"] == "http.disconnect":
                raise RuntimeError("client disconnect")

    async def body(self) -> bytes:
        if not self._body:
            body_chunks = bytearray()
            async for chunk in self.stream():
                body_chunks += chunk
            self._body = bytes(body_chunks)

        return self._body

    async def text(self, encoding="utf-8") -> str:
        if not self._text:
            self._text = (await self.body()).decode(encoding)

        return self._text

    async def json(self):
        body = await self.text()
        return json.loads(body)

    async def form(self):
        if not self._form:
            content_type = self.headers.get("content-type")
            if content_type is None or not _is_form(content_type):
                raise RuntimeError("request is not form")

            if FORM_MULTIPART_ENABLED and "multipart/form-data" in content_type:
                self._form = await process_form(self.stream(), self.headers)
            else:
                data = await self.text()
                self._form = parse_qs(data, keep_blank_values=True)

        return self._form
