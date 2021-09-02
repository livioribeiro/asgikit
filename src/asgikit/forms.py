import re
from collections.abc import AsyncIterable
from enum import Enum
from typing import Generator, NamedTuple, Union

RE_NAME = re.compile(rb"; name=\"(.*?)\"")
RE_FILENAME = re.compile(rb"; filename=\"(.*?)\"")
RE_CONTENT_TYPE = re.compile(rb"Content-Type: (.+)$")

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
    form_input: AsyncIterable[bytes], boundary: bytes
) -> AsyncIterable[ParseEvent]:
    async for data in form_input:
        for part in split_parts(data, boundary):
            if not part.removeprefix(b"\r\n").startswith(b"Content-Disposition"):
                yield ParseEvent(EventType.FILE_DATA, part)
                continue

            header, value = part.split(DATA_HEADER_SEPARATOR)
            name = next(iter(RE_NAME.findall(header)), None)
            filename = next(iter(RE_FILENAME.findall(header)), None)

            if name is not None and not filename:
                yield ParseEvent(
                    EventType.FORM_FIELD,
                    FormField(name.decode(), value.decode().strip()),
                )
            elif filename is not None:
                content_type = next(
                    iter(RE_CONTENT_TYPE.findall(header)),
                    b"application/octec-stream",
                )
                yield ParseEvent(
                    EventType.FORM_FILE,
                    FormFile(
                        name.decode(),
                        filename.decode(),
                        content_type.decode(),
                    ),
                )
                yield ParseEvent(EventType.FILE_DATA, value)
