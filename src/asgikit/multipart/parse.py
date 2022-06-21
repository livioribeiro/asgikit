import re
from enum import Enum
from typing import Any, AsyncIterable, NamedTuple

__all__ = (
    "EventType",
    "FormField",
    "FormFile",
    "ParseEvent",
    "EndEvent",
    "parse_multipart",
    "parse_part_header",
)

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
    event_type = EventType.END


async def parse_multipart(
    form_input: AsyncIterable[bytes], boundary: bytes
) -> AsyncIterable[ParseEvent]:
    async for part in _split_parts(form_input, boundary):
        if not part.removeprefix(b"\r\n").startswith(b"Content-Disposition"):
            yield ParseEvent(EventType.FILE_DATA, part)
            continue

        header, value = part.split(DATA_HEADER_SEPARATOR)
        parsed_header = parse_part_header(header)

        name = parsed_header["Content-Disposition"].get("name")
        filename = parsed_header["Content-Disposition"].get("filename")

        if name is not None and filename is None:
            yield ParseEvent(
                EventType.FORM_FIELD,
                FormField(name, value.decode().strip()),
            )
        elif filename is not None:
            content_type = parsed_header.get("Content-Type", {}).get("__value__")

            yield ParseEvent(
                EventType.FORM_FILE,
                FormFile(
                    name,
                    filename,
                    content_type,
                ),
            )
            yield ParseEvent(EventType.FILE_DATA, value)

    yield EndEvent()


async def _split_parts(
    data_input: AsyncIterable[bytes], boundary: bytes
) -> AsyncIterable[bytes]:
    separator = b"--" + boundary
    previous_chunk = b""

    async for data in data_input:
        current_chunk = data

        if separator in current_chunk:
            current_chunk = previous_chunk + current_chunk
            previous_chunk = b""

            *parts, rest = current_chunk.split(separator)
            for part in parts:
                if part:
                    part = part.removeprefix(b"\r\n").removesuffix(b"\r\n")
                    yield part

            if rest != b"--\r\n":
                previous_chunk = rest

            continue

        combined_chunk = previous_chunk + current_chunk
        if separator in combined_chunk:
            part, rest = combined_chunk.split(separator, 1)
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


def parse_part_header(header: bytes) -> dict[str, dict[str, Any]]:
    result = {}

    for field in header.removeprefix(b"\r\n").removesuffix(b"\r\n").split(b"\r\n"):
        field_dict = {}

        name, data = field.split(b":")
        name = name.decode()

        value, *properties = data.split(b";")
        value = value.decode().strip()
        field_dict["__value__"] = value

        for key, prop in (p.split(b"=") for p in properties):
            key = key.decode().strip()
            prop = prop.strip(b'"').decode()

            field_dict[key] = prop

        result[name] = field_dict

    return result
