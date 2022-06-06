import asyncio
import os
import tempfile
from collections.abc import AsyncIterable

from ..headers import Headers
from .parse import EventType, parse_multipart
from .uploaded_file import UploadedFile

__all__ = ["process_form"]


async def process_form(
    data_stream: AsyncIterable[bytes],
    headers: Headers,
) -> dict[str, str | UploadedFile]:
    content_type = headers.get_raw(b"content-type")
    boundary = content_type.split(b"boundary=")[1]

    result: dict[str, str | UploadedFile] = {}
    current_form_file: tuple[str, UploadedFile] | None = None
    current_form_file_fd = None

    try:
        async for event in parse_multipart(data_stream, boundary):
            if (
                current_form_file is not None
                and event.event_type != EventType.FILE_DATA
            ):
                name, uploaded_file = current_form_file
                result[name] = uploaded_file
                await asyncio.to_thread(os.close, current_form_file_fd)
                current_form_file = None
                current_form_file_fd = None

            match event.event_type:
                case EventType.FORM_FIELD:
                    result[event.event_value.name] = event.event_value.value
                case EventType.FORM_FILE:
                    current_form_file_fd, temp_name = tempfile.mkstemp()

                    uploaded_file = UploadedFile(
                        event.event_value.filename,
                        event.event_value.content_type,
                        temp_name,
                    )
                    current_form_file = event.event_value.name, uploaded_file
                case EventType.FILE_DATA:
                    await asyncio.to_thread(
                        os.write, current_form_file_fd, event.event_value
                    )
    finally:
        if current_form_file_fd is not None:
            await asyncio.to_thread(os.close, current_form_file_fd)

    return result
