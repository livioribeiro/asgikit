import asyncio
import os
from collections.abc import AsyncGenerator, AsyncIterable, Callable
from contextlib import asynccontextmanager
from io import BytesIO
from typing import ParamSpec, TypeVar

__all__ = ("AsyncFile",)

DEFAULT_ASYNC_FILE_CHUNK_SIZE = "4096"


T = TypeVar("T")
P = ParamSpec("P")


async def _exec(func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
    return await asyncio.to_thread(func, *args, **kwargs)


class AsyncFile:
    CHUNK_SIZE = int(
        os.getenv("ASGIKIT_ASYNC_FILE_CHUNK_SIZE", DEFAULT_ASYNC_FILE_CHUNK_SIZE)
    )

    __slots__ = ("__path", "__file", "__stat")

    def __init__(self, path: str | os.PathLike[bytes] | os.PathLike[str]):
        self.__path = path
        self.__file: BytesIO | None = None
        self.__stat: os.stat_result | None = None

    async def _open(self):
        self.__file = await _exec(open, self.__path, "rb")

    async def _read(self) -> bytes:
        return await _exec(self.__file.read, self.CHUNK_SIZE)

    async def _close(self):
        await _exec(self.__file.close)

    async def stat(self) -> os.stat_result:
        if self.__stat is None:
            self.__stat = await _exec(os.lstat, self.__path)
        return self.__stat

    @asynccontextmanager
    async def stream(self) -> AsyncGenerator[AsyncIterable[bytes]]:
        async def inner():
            while data := await self._read():
                yield data

        try:
            await self._open()
            yield inner()
        finally:
            await _exec(self.__file.close)
            self.__file = None

    def __del__(self):
        if self.__file and not self.__file.closed:
            self.__file.close()
