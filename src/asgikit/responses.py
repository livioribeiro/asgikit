import asyncio
import json
import mimetypes
import os
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager
from email.utils import formatdate
from enum import Enum
from http import HTTPStatus
from http.cookies import SimpleCookie
from os import PathLike
from typing import Any

import aiofiles
import aiofiles.os

from asgikit.asgi import AsgiProtocol, AsgiReceive, AsgiScope, AsgiSend
from asgikit.errors.http import ClientDisconnectError
from asgikit.headers import MutableHeaders

__all__ = (
    "SameSitePolicy",
    "HTTPStatus",
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


RESPONSE_KEY = "_response"


class SameSitePolicy(str, Enum):
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"


class Response:
    ENCODING = "utf-8"

    __slots__ = (
        "_asgi",
        "headers",
        "cookies",
        "content_type",
        "content_length",
        "encoding",
    )

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        self._asgi = AsgiProtocol(scope, receive, send)

        self.content_type: str | None = None
        self.content_length: int | None = None
        self.encoding = self.ENCODING

        self.headers = MutableHeaders()
        self.cookies = SimpleCookie()

        if RESPONSE_KEY not in self._asgi.scope:
            self._asgi.scope[RESPONSE_KEY] = {}

        if "is_started" not in self._asgi.scope[RESPONSE_KEY]:
            self._asgi.scope[RESPONSE_KEY]["is_started"] = False

        if "is_finished" not in self._asgi.scope[RESPONSE_KEY]:
            self._asgi.scope[RESPONSE_KEY]["is_finished"] = False

        if "status" not in self._asgi.scope[RESPONSE_KEY]:
            self._asgi.scope[RESPONSE_KEY]["status"] = None

    @property
    def is_started(self) -> bool:
        return self._asgi.scope[RESPONSE_KEY]["is_started"]

    @property
    def is_finished(self) -> bool:
        return self._asgi.scope[RESPONSE_KEY]["is_finished"]

    @property
    def status(self) -> HTTPStatus | None:
        return self._asgi.scope[RESPONSE_KEY]["status"]

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

    def _build_headers(self) -> list[tuple[bytes, bytes]]:
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
        if self.is_started:
            raise RuntimeError("response has already started")

        if self.is_finished:
            raise RuntimeError("response has already ended")

        self._asgi.scope[RESPONSE_KEY]["is_started"] = True
        self._asgi.scope[RESPONSE_KEY]["status"] = status

        headers = self._build_headers()
        await self._asgi.send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": headers,
            }
        )

    async def write(self, data: bytes | str, *, end_response=False):
        encoded_data = data if isinstance(data, bytes) else data.encode(self.encoding)

        if not self.is_started:
            raise RuntimeError("response was not started")

        await self._asgi.send(
            {
                "type": "http.response.body",
                "body": encoded_data,
                "more_body": not end_response,
            }
        )

        if end_response:
            self._asgi.scope[RESPONSE_KEY]["is_finished"] = True

    async def end(self):
        if not self.is_started:
            raise RuntimeError("response was not started")

        if self.is_finished:
            raise RuntimeError("response has already ended")

        await self.write(b"", end_response=True)


async def respond_text(
    response: Response, content: str, *, status: HTTPStatus = HTTPStatus.OK
):
    data = content.encode(response.encoding)
    if not response.content_type:
        response.content_type = "text/plain"

    response.content_length = len(data)

    await response.start(status)
    await response.write(data, end_response=True)


async def respond_status(response: Response, status: HTTPStatus):
    await response.start(status)
    await response.end()


async def respond_redirect(response: Response, location: str, permanent: bool = False):
    status = (
        HTTPStatus.TEMPORARY_REDIRECT
        if not permanent
        else HTTPStatus.PERMANENT_REDIRECT
    )

    response.header("location", location)
    await respond_status(response, status)


async def respond_redirect_post_get(response: Response, location: str):
    response.header("location", location)
    await respond_status(response, HTTPStatus.SEE_OTHER)


async def respond_json(response: Response, content: Any, status=HTTPStatus.OK):
    data = json.dumps(content).encode(response.encoding)

    response.content_type = "application/json"
    response.content_length = len(data)

    await response.start(status)
    await response.write(data, end_response=True)


async def _listen_for_disconnect(receive):
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return


@asynccontextmanager
async def stream_writer(response):
    client_disconect = asyncio.create_task(
        _listen_for_disconnect(response._asgi.receive)
    )

    async def write(data: bytes | str):
        if client_disconect.done():
            raise ClientDisconnectError()
        await response.write(data, end_response=False)

    try:
        yield write
    finally:
        await response.end()
        client_disconect.cancel()


async def respond_stream(
    response: Response, stream: AsyncIterable[bytes], *, status=HTTPStatus.OK
):
    await response.start(status)

    async with stream_writer(response) as write:
        async for chunk in stream:
            await write(chunk)


def _file_last_modified(stat: os.stat_result) -> str:
    return formatdate(stat.st_mtime, usegmt=True)


def _guess_mimetype(path: str | PathLike[str]) -> str | None:
    m_type, _ = mimetypes.guess_type(path, strict=False)
    return m_type


def _supports_pathsend(scope):
    return "extensions" in scope and "http.response.pathsend" in scope["extensions"]


def _supports_zerocopysend(scope):
    return "extensions" in scope and "http.response.zerocopysend" in scope["extensions"]


async def respond_file(
    response: Response, path: str | PathLike[str], status=HTTPStatus.OK
):
    if not response.content_type:
        response.content_type = _guess_mimetype(path)

    stat = await asyncio.to_thread(os.stat, path)
    content_length = stat.st_size
    last_modified = _file_last_modified(stat)

    response.content_length = content_length
    response.headers.set("last-modified", last_modified)

    if _supports_pathsend(response._asgi.scope):
        await response._asgi.send(
            {
                "type": "http.response.pathsend",
                "path": path,
            }
        )
        return

    if _supports_zerocopysend(response._asgi.scope):
        file = await asyncio.to_thread(open, path, "rb")
        await response._asgi.send(
            {
                "type": "http.response.zerocopysend",
                "file": file.fileno(),
            }
        )
        return

    async with aiofiles.open(path, "rb") as stream:
        await respond_stream(response, stream, status=status)
