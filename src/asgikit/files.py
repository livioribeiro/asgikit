import asyncio
from io import BytesIO
import os
from collections.abc import AsyncIterable
from concurrent.futures import ThreadPoolExecutor
from functools import partial

class AsyncFile:
    read_size = 1024

    def __init__(
        self,
        path: str,
        loop: asyncio.AbstractEventLoop = None,
        executor: ThreadPoolExecutor = None
    ):
        self.path = path
        self.loop = loop or asyncio.get_event_loop()
        self.executor = executor

    async def _exec(self, func, /, *args, **kwargs):
        return await self.loop.run_in_executor(self.executor, partial(func, *args, **kwargs))

    async def _open(self) -> BytesIO:
        return await self._exec(open, self.path, "rb")

    async def stat(self) -> os.stat_result:
        return await self._exec(os.stat, self.path)

    async def stream(self) -> AsyncIterable[bytes]:
        fd = await self._open()
        try:
            while (data := await self._exec(fd.read, self.read_size)):
                yield data
        finally:
            await self._exec(fd.close)


class AsyncFileReader:
    """Attempt to read a file assyncronously"""
    def __init__(self, loop):
        self.loop = loop
        self.fd = None
        self.future = None

    @staticmethod
    async def open(path: str, loop=None):
        self = AsyncFile(loop or asyncio.get_event_loop())
        self.fd = await self.loop.run_in_executor(
            None,
            partial(os.open, path, os.O_RDONLY | os.O_NONBLOCK)
        )
        return self

    def _read(self, n):
        res = os.read(self.fd, n)
        if res is None: # would block
            self.loop.call_soon(self._read, n)
        else:
            self.future.set_result(res)

    def read(self, n):
        self.future = self.loop.create_future()
        self.loop.call_soon(self._read, n)
        return self.future
