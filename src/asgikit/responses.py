from __future__ import annotations

import asyncio
import json
import mimetypes
import os
from asyncio import AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor
from collections.abc import AsyncIterable
from email.utils import formatdate
from enum import Enum
from http import HTTPStatus
from http.cookies import SimpleCookie
from typing import Any, Optional

from asgikit.files import AsyncFile

from .headers import MutableHeaders


def _supports_zerocopysend(scope):
    return "extensions" in scope and "http.response.zerocopysend" in scope["extensions"]


async def _listen_for_disconnect(receive):
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return


class SameSitePolicy(str, Enum):
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"


class HttpResponse:
    content_type = None
    encoding = "utf-8"

    def __init__(
        self,
        status: HTTPStatus = HTTPStatus.OK,
        content: Any = None,
        content_type: str = None,
        encoding: str = None,
        headers: MutableHeaders | dict[str, str] | dict[str, list[str]] = None,
    ):
        self.status = status
        self.content = content

        if content_type is not None:
            self.content_type = content_type

        if encoding is not None:
            self.encoding = encoding

        if headers is None:
            self.headers = MutableHeaders()
        elif isinstance(headers, MutableHeaders):
            self.headers = headers
        elif isinstance(headers, (dict, list)):
            self.headers = MutableHeaders(headers)
        else:
            raise ValueError("'headers' must be instance of 'dict[str, str | list[str]' or 'MutableHeaders'")

        self.cookies = SimpleCookie()

        self._is_initialized = False
        self._body = None

    def header(self, name: str, value: str) -> HttpResponse:
        self.headers.set(name, value)
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
    ) -> HttpResponse:
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

    async def build_body(self) -> Optional[bytes]:
        if self.content is None:
            body = None
        elif isinstance(self.content, bytes):
            body = self.content
        else:
            body = str(self.content).encode(self.encoding)

        return body

    async def _build_body(self):
        self._body = await self.build_body() or b""

    async def get_content_length(self) -> Optional[int]:
        if "content-length" not in self.headers and self._body is not None:
            return len(self._body)
        return 0

    async def build_headers(self) -> list[tuple[bytes, bytes]]:
        if (content_length := await self.get_content_length()) is not None:
            self.header("content-length", str(content_length))

        if self.content_type is not None:
            if self.content_type.startswith("text/"):
                content_type = f"{self.content_type}; charset={self.encoding}"
            else:
                content_type = self.content_type

            self.header("content-type", content_type)

        return self.headers.encode()

    async def init_response(self, _scope, _receive, send):
        if self._is_initialized:
            raise RuntimeError("response is already initialized")

        self._is_initialized = True

        await self._build_body()
        headers = await self.build_headers()
        await send(
            {
                "type": "http.response.start",
                "status": self.status,
                "headers": headers,
            }
        )

    async def send_response(self, _scope, _receive, send):
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

    async def build_body(self) -> bytes:
        if self.content:
            return json.dumps(self.content).encode(self.encoding)


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

    async def build_body(self) -> Optional[bytes]:
        return None

    async def get_content_length(self) -> Optional[int]:
        return None

    async def _send_response(self, send):
        async for chunk in self.stream:
            if isinstance(chunk, str):
                chunk = chunk.encode(self.encoding)

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

    async def send_response(self, _scope, receive, send):
        coroutines = [_listen_for_disconnect(receive), self._send_response(send)]
        tasks = map(asyncio.create_task, coroutines)

        _, pending_tasks = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending_tasks:
            task.cancel()


class FileResponse(StreamingResponse):
    def __init__(
        self,
        path: str,
        content_type=None,
        headers=None,
        *,
        loop: AbstractEventLoop = None,
        executor: ThreadPoolExecutor = None,
    ):
        if content_type is None:
            m_type, _ = mimetypes.guess_type(path, strict=False)
            if m_type:
                content_type = m_type

        super().__init__(None, content_type, headers)
        self.path = path
        self._stat = None

        if loop is not None:
            self._file = AsyncFile(path, loop, executor)
        else:
            self._file = None

    async def get_file(self) -> AsyncFile:
        if self._file is None:
            self._file = AsyncFile(self.path, asyncio.get_running_loop())
        return self._file

    async def get_stat(self) -> os.stat_result:
        if self._stat is None:
            file = await self.get_file()
            self._stat = await file.stat()
        return self._stat

    async def get_content_length(self) -> Optional[int]:
        stat = await self.get_stat()
        return stat.st_size

    async def build_headers(self) -> list[tuple[bytes, bytes]]:
        stat = await self.get_stat()
        last_modified = formatdate(stat.st_mtime, usegmt=True)
        self.headers.set("last-modified", last_modified)
        return await super().build_headers()

    async def send_response(self, scope, receive, send):
        if _supports_zerocopysend(scope):
            file = open(self.path, "rb")
            await send(
                {
                    "type": "http.response.zerocopysend",
                    "file": file.fileno(),
                }
            )
            return

        file = await self.get_file()
        self.stream = file.stream()
        return await super().send_response(scope, receive, send)
