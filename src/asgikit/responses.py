import asyncio
import json
from enum import Enum
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import Any, AsyncIterable, Optional, Union

from .headers import MutableHeaders


class SameSitePolicy(str, Enum):
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"


class HttpResponse:
    content_type = None
    charset = "utf-8"

    def __init__(
        self,
        status: HTTPStatus = HTTPStatus.OK,
        content: Any = None,
        content_type: str = None,
        charset: str = None,
        headers: Union[MutableHeaders, dict] = None,
    ):
        self.status = status
        self.content = content

        if content_type is not None:
            self.content_type = content_type

        if charset is not None:
            self.charset = charset

        if headers is None:
            self.headers = MutableHeaders()
        elif isinstance(headers, MutableHeaders):
            self.headers = headers
        elif isinstance(headers, dict):
            self.headers = MutableHeaders(headers)
        else:
            raise ValueError("'headers' must be instance of 'dict' or 'MutableHeaders'")

        self.cookies = SimpleCookie()

        self._is_initialized = False
        self._body = None

    def header(self, name: str, value: str) -> "HttpResponse":
        self.headers.add(name, value)
        return self

    def cookie(
        self,
        name: str,
        value: str,
        expires: int = None,
        domain: str = None,
        path: str = None,
        max_age: int = None,
        secure: bool = False,
        httponly: bool = True,
        samesite: SameSitePolicy = SameSitePolicy.LAX,
    ) -> "HttpResponse":
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

        return self

    def build_body(self) -> Optional[bytes]:
        if self.content is None:
            body = None
        elif isinstance(self.content, bytes):
            body = self.content
        else:
            body = str(self.content).encode(self.charset)

        return body

    def _build_body(self):
        self._body = self.build_body() or b""

    def get_content_length(self) -> Optional[int]:
        if "content-length" not in self.headers and self._body is not None:
            return len(self._body)
        return 0

    def build_headers(self) -> list[tuple[bytes, bytes]]:
        if (content_length := self.get_content_length()) is not None:
            self.header("content-length", str(content_length))

        if self.content_type is not None:
            if self.content_type.startswith("text/"):
                content_type = f"{self.content_type}; charset={self.charset}"
            else:
                content_type = self.content_type

            self.header("content-type", content_type)

        return self.headers.encode()

    async def init_response(self, scope, receive, send):
        if self._is_initialized:
            raise RuntimeError("response is already initialized")

        self._is_initialized = True

        self._build_body()
        headers = self.build_headers()
        await send(
            {
                "type": "http.response.start",
                "status": self.status,
                "headers": headers,
            }
        )

    async def send_response(self, scope, receive, send):
        if not self._is_initialized:
            raise RuntimeError("response is not initialized")

        await send(
            {
                "type": "http.response.body",
                "body": self._body,
                "more_body": False,
            }
        )

    async def __call__(self, scope, receive, send):
        await self.init_response(scope, receive, send)
        await self.send_response(scope, receive, send)


class PlainTextResponse(HttpResponse):
    content_type = "text/plain"


class JsonResponse(HttpResponse):
    content_type = "application/json"

    def build_body(self) -> bytes:
        if self.content:
            return json.dumps(self.content).encode(self.charset)


class RedirectResponse(HttpResponse):
    def __init__(self, location: str, permanent: bool = False, headers=None):
        status = (
            HTTPStatus.TEMPORARY_REDIRECT
            if not permanent
            else HTTPStatus.PERMANENT_REDIRECT
        )
        super().__init__(status, headers=headers)
        self.header("location", location)


class RedirectPostGetResponse(HttpResponse):
    def __init__(self, location: str, headers=None):
        status = HTTPStatus.SEE_OTHER
        super().__init__(status, headers=headers)
        self.header("location", location)


class StreamingResponse(HttpResponse):
    def __init__(
        self, stream: AsyncIterable[bytes], content_type: str = None, headers=None
    ):
        super().__init__(content=None, content_type=content_type, headers=headers)
        self.stream = stream

    def build_body(self) -> Optional[bytes]:
        return None

    def get_content_length(self) -> Optional[int]:
        return None

    async def init_response(self, scope, receive, send):
        return await super().init_response(scope, receive, send)

    async def _listen_for_disconnect(self, receive):
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return

    async def _send_response(self, send):
        async for chunk in self.stream:
            if not isinstance(chunk, bytes):
                chunk = chunk.encode(self.charset)

            await send(
                {
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                }
            )

        await send(
            {
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            }
        )

    async def send_response(self, scope, receive, send):
        coroutines = [self._listen_for_disconnect(receive), self._send_response(send)]
        tasks = map(asyncio.create_task, coroutines)

        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
