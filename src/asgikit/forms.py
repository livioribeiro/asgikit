import asyncio
import os
import shutil
from collections import defaultdict
from collections.abc import AsyncIterable
from dataclasses import dataclass
from io import BytesIO
from tempfile import SpooledTemporaryFile

from multipart import MultipartSegment, PushMultipartParser

MAX_SPOOL_FILE_SIZE = 1024 * 1024


@dataclass
class UploadedFile:
    file: SpooledTemporaryFile
    filename: str
    content_type: str
    size: int

    def __copy_file(self, dst: str | os.PathLike):
        with self.file as src_fd, open(dst, "wb") as dst_fd:
            shutil.copyfileobj(src_fd, dst_fd)

    async def copy_file(self, dst: str | os.PathLike):
        await asyncio.to_thread(self.__copy_file, dst)


async def process_multipart(reader: AsyncIterable[bytes], boundary: str):
    form_result = defaultdict(list)

    current_segment: MultipartSegment = None
    current_value: BytesIO = None
    current_file: SpooledTemporaryFile = None
    current_is_file: bool = False

    with PushMultipartParser(boundary) as parser:
        while not parser.closed:
            async for chunk in reader:
                for result in parser.parse(chunk):
                    if isinstance(result, MultipartSegment):
                        current_segment = result
                        if result.filename:
                            current_is_file = True
                            current_file = SpooledTemporaryFile(
                                max_size=MAX_SPOOL_FILE_SIZE,
                                mode="w+b",
                            )
                            current_value = None
                        else:
                            current_is_file = False
                            current_value = BytesIO()
                            current_file = None
                    elif result:  # Non-empty bytearray
                        if current_is_file:
                            await asyncio.to_thread(current_file.write, result)
                        else:
                            current_value.write(result)
                    else:  # None
                        if current_is_file:
                            await asyncio.to_thread(current_file.seek, 0)
                            form_result[current_segment.name].append(
                                UploadedFile(
                                    file=current_file,
                                    filename=current_segment.filename,
                                    content_type=current_segment.content_type,
                                    size=current_segment.size,
                                )
                            )
                        else:
                            current_value.seek(0)
                            form_result[current_segment.name].append(
                                current_value.read().decode()
                            )
            parser.close(check_complete=True)
    return form_result
