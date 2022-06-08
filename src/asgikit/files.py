import asyncio
import os
from collections.abc import AsyncIterable
from io import BytesIO

__all__ = ("AsyncFile",)

DEFAULT_ASYNC_FILE_CHUNK_SIZE = "4096"


async def _exec(func, /, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


class AsyncFile:
    CHUNK_SIZE = int(
        os.getenv("ASGIKIT_ASYNC_FILE_CHUNK_SIZE", DEFAULT_ASYNC_FILE_CHUNK_SIZE)
    )

    __slots__ = ("path",)

    def __init__(self, path: str):
        self.path = path

    async def _open(self) -> BytesIO:
        return await _exec(open, self.path, "rb")

    async def stat(self) -> os.stat_result:
        return await _exec(os.stat, self.path)

    async def stream(self) -> AsyncIterable[bytes]:
        file = await self._open()
        try:
            while data := await _exec(file.read, self.CHUNK_SIZE):
                yield data
        finally:
            await _exec(file.close)
