import re
from enum import Enum
from typing import AsyncIterable, NamedTuple

__all__ = [
    "EventType",
    "FormField",
    "FormFile",
    "ParseEvent",
    "EndEvent",
    "parse_multipart",
]

RE_NAME = re.compile(rb"; name=\"(.*?)\"")
RE_FILENAME = re.compile(rb"; filename=\"(.*?)\"")
RE_CONTENT_TYPE = re.compile(rb"Content-Type: (.+)$")

DATA_HEADER_SEPARATOR = b"\r\n\r\n"


class EventType(Enum):
    FORM_FIELD = 1
    FORM_FILE = 2
    FILE_DATA = 3
    END = 4


class FormField(NamedTuple):
    name: str
    value: str


class FormFile(NamedTuple):
    name: str
    filename: str
    content_type: str


class ParseEvent(NamedTuple):
    event_type: EventType
    event_value: FormField | FormFile | bytes


class EndEvent(NamedTuple):
    event_type: EventType = EventType.END


async def parse_multipart(
    form_input: AsyncIterable[bytes], boundary: bytes
) -> AsyncIterable[ParseEvent]:
    async for part in _split_parts(form_input, boundary):
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

    yield EndEvent()


async def _split_parts(
    data_input: AsyncIterable[bytes], boundary: bytes
) -> AsyncIterable[bytes]:
    boundary = b"--" + boundary
    previous_chunk = b""

    async for data in data_input:
        current_chunk = data

        if boundary in current_chunk:
            current_chunk = previous_chunk + current_chunk
            previous_chunk = b""

            *parts, rest = current_chunk.split(boundary)
            for part in parts:
                if part:
                    part = part.removeprefix(b"\r\n").removesuffix(b"\r\n")
                    yield part

            if rest != b"--\r\n":
                previous_chunk = rest

            continue

        combined_chunk = previous_chunk + current_chunk
        if boundary in combined_chunk:
            part, rest = combined_chunk.split(boundary, 1)
            yield part.removesuffix(b"\r\n")
            previous_chunk = rest.removeprefix(b"\r\n") if rest != b"--\r\n" else b""
        elif combined_chunk.startswith(b"\r\nContent-Disposition"):
            yield combined_chunk
            previous_chunk = b""
        else:
            if previous_chunk:
                yield previous_chunk
            previous_chunk = current_chunk

    if previous_chunk:
        yield previous_chunk
