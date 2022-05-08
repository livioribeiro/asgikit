import asyncio
import os
import tempfile
from asyncio import AbstractEventLoop
from collections.abc import AsyncIterable
from concurrent.futures import ThreadPoolExecutor

from ..headers import Headers
from .parse import EventType, parse_multipart
from .uploaded_file import UploadedFile


async def process_form(
    data_stream: AsyncIterable[bytes],
    headers: Headers,
    loop: AbstractEventLoop = None,
    executor: ThreadPoolExecutor = None,
) -> dict[str, str | UploadedFile]:
    content_type = headers.get_raw(b"content-type")
    boundary = content_type.split(b"boundary=")[1]

    loop = loop or asyncio.get_running_loop()

    result = {}
    current_form_file: tuple[str, UploadedFile] = None
    current_form_file_fd = None

    try:
        async for event in parse_multipart(data_stream, boundary):
            if event.event_type != EventType.FILE_DATA and current_form_file is not None:
                name, uploaded_file = current_form_file
                result[name] = uploaded_file
                current_form_file = None
                await loop.run_in_executor(executor, os.close, current_form_file_fd)
                current_form_file_fd = None

            if event.event_type == EventType.FORM_FIELD:
                result[event.event_value.name] = event.event_value.value
            elif event.event_type == EventType.FORM_FILE:
                current_form_file_fd, temp_name = tempfile.mkstemp()

                current_form_file = event.event_value.name, UploadedFile(
                    event.event_value.filename,
                    event.event_value.content_type,
                    temp_name,
                )
            elif event.event_type == EventType.FILE_DATA:
                await loop.run_in_executor(
                    executor, os.write, current_form_file_fd, event.event_value
                )
    finally:
        if current_form_file_fd is not None:
            await loop.run_in_executor(executor, os.close, current_form_file_fd)

    return result
