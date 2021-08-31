import re
from collections.abc import AsyncIterable
from enum import Enum
from typing import Generator, NamedTuple, Union

RE_NAME = re.compile(br"; name=\"(.*?)\"")
RE_FILENAME = re.compile(br"; filename=\"(.*?)\"")
RE_CONTENT_TYPE = re.compile(br"Content-Type: (.+)$")

DATA_HEADER_SEPARATOR = b"\r\n\r\n"


class EventType(Enum):
    FORM_FIELD = 1
    FORM_FILE = 2
    FILE_DATA = 3


class FormField(NamedTuple):
    name: str
    value: str


class FormFile(NamedTuple):
    name: str
    filename: str
    content_type: str


class ParseEvent(NamedTuple):
    event_type: EventType
    event_value: Union[FormField, FormFile, bytes]


def split_parts(data: bytes, boundary: bytes) -> Generator[bytes, None, None]:
    for part in data.split(b"--" + boundary):
        if part == b"":
            continue
        yield part


async def parse_multipart(
    input: AsyncIterable[bytes], boundary: bytes
) -> AsyncIterable[ParseEvent]:
    async for data in input:
        for part in split_parts(data, boundary):
            if not part.removeprefix(b"\r\n").startswith(b"Content-Disposition"):
                yield ParseEvent(EventType.FILE_DATA, part)
                continue

            header, value = part.split(DATA_HEADER_SEPARATOR)
            name = RE_NAME.findall(header)
            filename = RE_FILENAME.findall(header)

            if name and not filename:
                yield ParseEvent(
                    EventType.FORM_FIELD,
                    FormField(name[0].decode(), value.decode().strip()),
                )
            elif filename:
                content_type = RE_CONTENT_TYPE.findall(header)
                yield ParseEvent(
                    EventType.FORM_FILE,
                    FormFile(
                        name[0].decode(),
                        filename[0].decode(),
                        content_type[0].decode(),
                    ),
                )
                yield ParseEvent(EventType.FILE_DATA, value)
