import asyncio
import json
import mimetypes
import os
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from email.utils import formatdate
from enum import Enum
from functools import singledispatchmethod
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Optional

import aiofiles

from asgikit.errors.http import ClientDisconnectError
from asgikit.headers import MutableHeaders
from asgikit.http import AsgiContext

__all__ = (
    "SameSitePolicy",
    "HTTPStatus",
    "HttpResponse",
    "respond_text",
    "respond_status",
    "respond_redirect",
    "respond_redirect_post_get",
    "respond_json",
    "respond_stream",
    "respond_file",
)


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
    ENCODING = "utf-8"

    __slots__ = (
        "_context",
        "headers",
        "cookies",
        "content_type",
        "content_length",
        "encoding",
        "_is_started",
        "_is_finished",
    )

    def __init__(self, scope, receive, send):
        self._context = AsgiContext(scope, receive, send)

        self.content_type: str | None = None
        self.content_length: int | None = None
        self.encoding = self.ENCODING

        self.headers = MutableHeaders()
        self.cookies = SimpleCookie()

        self._is_started = False
        self._is_finished = False

    @property
    def is_started(self) -> bool:
        return self._is_started

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    def header(self, name: str, value: str):
        self.headers.set(name, value)

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
    ):
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

    async def _build_headers(self) -> list[tuple[bytes, bytes]]:
        if self.content_type is not None:
            if self.content_type.startswith("text/"):
                content_type = f"{self.content_type}; charset={self.encoding}"
            else:
                content_type = self.content_type

            self.header("content-type", content_type)

        if self.content_length is not None:
            self.header("content-length", str(self.content_length))

        return self.headers.encode()

    async def start(self, status=HTTPStatus.OK):
        if self._is_started:
            raise RuntimeError("response has already started")

        if self._is_finished:
            raise RuntimeError("response has already ended")

        self._is_started = True

        headers = await self._build_headers()
        await self._context.send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": headers,
            }
        )

    @singledispatchmethod
    async def write(self, data, *, response_end=False):
        raise NotImplementedError("non typed write")

    @write.register
    async def _(self, data: bytes, *, response_end=False):
        if not self._is_started:
            raise RuntimeError("response was not started")

        await self._context.send(
            {
                "type": "http.response.body",
                "body": data,
                "more_body": not response_end,
            }
        )

        if response_end:
            self._is_finished = True

    @write.register
    async def _(self, data: str, *, response_end=False):
        await self.write(data.encode(self.encoding), response_end=response_end)

    async def end(self):
        if not self._is_started:
            raise RuntimeError("response was not started")

        if self._is_finished:
            raise RuntimeError("response has already ended")

        await self.write(b"", response_end=True)

    @asynccontextmanager
    async def stream_writer(self):
        client_disconect = asyncio.create_task(_listen_for_disconnect(self._context.receive))

        async def write(data: bytes | str):
            if client_disconect.done():
                raise ClientDisconnectError()
            await self.write(data, response_end=False)

        try:
            yield write
        finally:
            await self.end()
            client_disconect.cancel()


async def respond_text(
    response: HttpResponse, content: str, *, status: HTTPStatus = HTTPStatus.OK
):
    data = content.encode(response.encoding)
    if not response.content_type:
        response.content_type = "text/plain"

    response.content_length = len(data)

    await response.start(status)
    await response.write(data, response_end=True)


async def respond_status(response: HttpResponse, status: HTTPStatus):
    await response.start(status)
    await response.end()


async def respond_redirect(
    response: HttpResponse, location: str, permanent: bool = False
):
    status = (
        HTTPStatus.TEMPORARY_REDIRECT
        if not permanent
        else HTTPStatus.PERMANENT_REDIRECT
    )

    response.header("location", location)
    await respond_status(response, status)


async def respond_redirect_post_get(response: HttpResponse, location: str):
    response.header("location", location)
    await respond_status(response, HTTPStatus.SEE_OTHER)


async def respond_json(response: HttpResponse, content: Any, status=HTTPStatus.OK):
    data = json.dumps(content).encode(response.encoding)

    response.content_type = "application/json"
    response.content_length = len(data)

    await response.start(status)
    await response.write(data, response_end=True)


async def _file_stat(path: Path) -> os.stat_result:
    return await asyncio.to_thread(os.stat, path)


def _file_content_length(stat: os.stat_result) -> Optional[int]:
    return stat.st_size


def _file_last_modified(stat: os.stat_result) -> str:
    return formatdate(stat.st_mtime, usegmt=True)


def _guess_mimetype(path: Path) -> str | None:
    m_type, _ = mimetypes.guess_type(path, strict=False)
    return m_type


def _supports_zerocopysend(scope):
    return "extensions" in scope and "http.response.zerocopysend" in scope["extensions"]


async def respond_stream(
    response: HttpResponse, stream: AsyncIterable[bytes], *, status=HTTPStatus.OK
):
    await response.start(status)

    async with response.stream_writer() as write:
        async for chunk in stream:
            await write(chunk)


async def respond_file(response: HttpResponse, path: Path, status=HTTPStatus.OK):
    if not response.content_type:
        response.content_type = _guess_mimetype(path)

    stat = await _file_stat(path)
    content_length = _file_content_length(stat)
    last_modified = _file_last_modified(stat)

    response.content_length = content_length
    response.headers.set("last-modified", last_modified)

    if _supports_zerocopysend(response._context.scope):
        file = await asyncio.to_thread(open, path, "rb")
        await response._context.send(
            {
                "type": "http.response.zerocopysend",
                "file": file.fileno(),
            }
        )
        return

    async with aiofiles.open(path, 'rb') as stream:
        await respond_stream(response, stream, status=status)
