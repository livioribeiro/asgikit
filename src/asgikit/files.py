import asyncio
import os
from asyncio import AbstractEventLoop
from collections.abc import AsyncIterable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from io import BytesIO

__all__ = ["AsyncFile"]

DEFAULT_ASYNC_FILE_CHUNK_SIZE = "4096"


class AsyncFile:
    CHUNK_SIZE = int(
        os.getenv("ASGIKIT_ASYNC_FILE_CHUNK_SIZE", DEFAULT_ASYNC_FILE_CHUNK_SIZE)
    )

    __slots__ = ["path"]

    def __init__(self, path: str):
        self.path = path

    async def _exec(self, func, /, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    async def _open(self) -> BytesIO:
        return await self._exec(open, self.path, "rb")

    async def stat(self) -> os.stat_result:
        return await self._exec(os.stat, self.path)

    async def stream(self) -> AsyncIterable[bytes]:
        file = await self._open()
        try:
            while data := await self._exec(file.read, self.CHUNK_SIZE):
                yield data
        finally:
            await self._exec(file.close)
