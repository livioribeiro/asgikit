import asyncio
from collections.abc import AsyncIterable
from tempfile import SpooledTemporaryFile

from ..headers import Headers
from .parse import EventType, parse_multipart
from .uploaded_file import UploadedFile

__all__ = ("process_form",)

UPLOAD_FILE_DISK_THRESHOULD = 4096


async def process_form(
    data_stream: AsyncIterable[bytes],
    headers: Headers,
) -> dict[str, str | UploadedFile]:
    content_type = headers.get_raw(b"content-type")
    boundary = content_type.split(b"boundary=")[1]

    result: dict[str, str | UploadedFile] = {}
    current_form_file: tuple[str, UploadedFile] | None = None
    temporary_uploaded_file: SpooledTemporaryFile | None = None

    try:
        async for event in parse_multipart(data_stream, boundary):
            if (
                current_form_file is not None
                and event.event_type != EventType.FILE_DATA
            ):
                name, uploaded_file = current_form_file
                result[name] = uploaded_file
                await asyncio.to_thread(temporary_uploaded_file.seek, 0)

                current_form_file = None
                temporary_uploaded_file = None

            match event.event_type:
                case EventType.FORM_FIELD:
                    result[event.event_value.name] = event.event_value.value
                case EventType.FORM_FILE:
                    temporary_uploaded_file = SpooledTemporaryFile(
                        UPLOAD_FILE_DISK_THRESHOULD
                    )

                    uploaded_file = UploadedFile(
                        event.event_value.filename,
                        event.event_value.content_type,
                        temporary_uploaded_file,
                    )
                    current_form_file = event.event_value.name, uploaded_file
                case EventType.FILE_DATA:
                    await asyncio.to_thread(
                        temporary_uploaded_file.write, event.event_value
                    )
    finally:
        if temporary_uploaded_file is not None:
            await asyncio.to_thread(temporary_uploaded_file.seek, 0)

    return result
