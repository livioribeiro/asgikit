import asyncio
import os
from asyncio import AbstractEventLoop
from collections.abc import AsyncIterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Union

from ..headers import Headers
from .multipart import EventType, parse_multipart


def _move(src, target: Path):
    try:
        src.seek(0)
        with target.open("wb") as dest:
            while chunk := src.read(4096):
                dest.write(chunk)
    finally:
        src.close()


@dataclass
class UploadedFile:
    filename: str
    content_type: str
    file: SpooledTemporaryFile

    async def move_file(self, target: Union[str, Path]):
        if isinstance(target, str):
            target = Path(target)
        if target.is_dir():
            target = target / self.filename

        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, _move, self.file, target)


async def process_form(
    data_stream: AsyncIterable[bytes],
    headers: Headers,
    loop: AbstractEventLoop = None,
    executor: ThreadPoolExecutor = None,
) -> dict[str, Union[str, UploadedFile]]:
    content_type = headers.get_raw(b"content-type")
    boundary = content_type.split(b"boundary=")[1]

    loop = loop or asyncio.get_running_loop()

    result = {}
    current_form_file = None

    async for e in parse_multipart(data_stream, boundary):
        if e.event_type != EventType.FILE_DATA and current_form_file is not None:
            name, uploaded_file = current_form_file
            result[name] = uploaded_file
            current_form_file = None

        if e.event_type == EventType.FORM_FIELD:
            result[e.event_value.name] = e.event_value.value
        elif e.event_type == EventType.FORM_FILE:
            current_form_file = e.event_value.name, UploadedFile(
                e.event_value.filename,
                e.event_value.content_type,
                SpooledTemporaryFile(max_size=1024, suffix=e.event_value.filename),
            )
        elif e.event_type == EventType.FILE_DATA:
            await loop.run_in_executor(
                executor, partial(current_form_file[1].file.write, e.event_value)
            )

    return result
