import asyncio
import os
from collections.abc import AsyncIterable
from io import BytesIO
from pathlib import Path

__all__ = ("AsyncFile",)

DEFAULT_ASYNC_FILE_CHUNK_SIZE = "4096"


async def _exec(func, /, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


class AsyncFile:
    CHUNK_SIZE = int(
        os.getenv("ASGIKIT_ASYNC_FILE_CHUNK_SIZE", DEFAULT_ASYNC_FILE_CHUNK_SIZE)
    )

    __slots__ = ("path", "file")

    def __init__(self, path: str | Path):
        self.path = path
        self.file: BytesIO | None = None

    async def _open(self):
        self.file = await _exec(open, self.path, "rb")

    async def _read(self) -> bytes:
        return await _exec(self.file.read, self.CHUNK_SIZE)

    async def _close(self):
        await _exec(self.file.close)

    async def stat(self) -> os.stat_result:
        return await _exec(os.stat, self.path)

    async def stream(self) -> AsyncIterable[bytes]:
        try:
            await self._open()
            while data := await self._read():
                yield data
        finally:
            await _exec(self.file.close)
            self.file = None

    def __del__(self):
        if self.file and not self.file.closed:
            self.file.close()
