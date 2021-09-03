import asyncio
import os
from collections.abc import AsyncIterable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from io import BytesIO


class AsyncFile:
    chunk_size = 4096

    def __init__(
        self,
        path: str,
        loop: asyncio.AbstractEventLoop = None,
        executor: ThreadPoolExecutor = None,
    ):
        self.path = path
        self.loop = loop or asyncio.get_event_loop()
        self.executor = executor

    async def _exec(self, func, /, *args, **kwargs):
        return await self.loop.run_in_executor(
            self.executor, partial(func, *args, **kwargs)
        )

    async def _open(self) -> BytesIO:
        return await self._exec(open, self.path, "rb")

    async def stat(self) -> os.stat_result:
        return await self._exec(os.stat, self.path)

    async def stream(self) -> AsyncIterable[bytes]:
        fd = await self._open()
        try:
            while data := await self._exec(fd.read, self.chunk_size):
                yield data
        finally:
            await self._exec(fd.close)
