import asyncio
from pathlib import Path

import pytest
from python_multipart import multipart

from asgikit.headers import Headers
from asgikit.requests import Request, read_form
from tests.utils.asgi import asgi_receive_from_stream

CRLF = b"\r\n"
BOUNDARY = b"-------------------------34361615033664377796334469137"
FILE_DATA = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x06bKGD\x00\xff\x00\xff\x00\xff\xa0\xbd\xa7\x93\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xd8\x04\x1b\x118!\x063'^\x00\x00\x027IDAT8\xcbe\x93OHUA\x14\x87\xbf{\xdf\xb3w{\"\x94\x10\xa5\xd1&hS\x8b6\xadZ\xb4\x10\x1emB*xP\xdb\xc0MQ\xae\xdd\x04A\x8b \"\xda)mZH\x1b\x17\x91 F\x11EF\x98\x96\xb6\xb5\x88\xcc2\x15\xd4\xfc\xf3\xee\x9dy3g\xe6\xb6\xf0\xde\xbc\xea\x81\xc3\xc0\xcc\xf7;\xe77\xcc\x9c\x80]\xd1\xfd\xe0\xed3i\x9as\xde\x99v\xb1M\xc4\x18\xa4\xa9\xb4U\xfa\xf1\xc7\xfe\xeb}\x80\x06\\\xce\x87\xbb\x0bx'\x17G\xfaj\xedN,\xceZ\xbcX\xbcwQ\x1a\xf8\x9b\xc01 *\xf2{\n8k9\x7fg\x18'v;\xad\xcd\x8f;\x80j\x91/\x03t?|\x7f\xdb[{\\\xac\n\x8cN\x06\x8dj\x94E\xc7%g\x0c\xe1\xbeJ=M}\xceW\x80\xd2\x8e\x02\x97\x1f}x\xed\xc4v\xa5^\xc0{\x02\xa0Tn\x81J\x15\x82\x12N\xec\x0e\x87\xe9\\}\xc1\xdbX\x8bn\xdc\xaf\x9czw/\xf4\xdeumY5;mg\x99\x87\xa8\xcdQ\xc0\"\t\xa1SQ\x19}\x03\xe8,\xe7\xa0/\x88|\xe1\xdei\xea\xb5\xd3\xf1\x9b\xa9'}\x03\xcbS\xb5\x1a\xa2@\x12B\xaf\xda\x81\x8e\xf2\x0e\xb1\xb5\xe8\xc6\xda\xe8\xfc\xf8\xf0\xd3\xf9\xe9Wk\x80\x00)`\xe6\xc6j'\x0f\xb6J/N\x81K@\x12\x80\xfde1M\xed\xc5FN,j}yhb\xa0wp\xe3\xe7\xad+\xad\xd1\x89K\xa1S\xd1\x7fXb\xf2\xee\x88\xc2\x8b\xd6@\x10:\x91\xd9\xdc\xfa\x9f\xc9\x97\xcf\xe3_\xbd=mU\x7f5\xf4EqR\x10'\xe04I\x92N\x02&t:\xee\x17c\xb4\x13\xcb\xef\xa9\x91\xb5j\xe4.l\x0b\n\xa2\x82\x18`zF\xbf\x006\x83\xecgu\x00G\x81f\xbapm\"\x87\x97\x16\xff\x0e\x95\xbcJ\xb7\x9c(p\n\x80o\xb3\xe6\xcb\xd9\x9e\xd5q\xe0G\x190\xc0\"\xb0\x01\xa4\xc5n\x87\x0f\xb8:\"\xe0,\x88%8\xb3\xd8\x054\x00\x95\xf1+!\xe0\xb3\x8d\x15`\xd5\xdbDoY-\xe4\xe9\xaf\xf84\xd5\xd9\x8b,\x00\xdf\xb35\xd93\x0b\x8d\x8d\xf5\xba\xd5\xf1gob\x9d;\xb1\xe3\x9d3c\x9f\xd4]\xc0\x02I\xd6\xd0\x02i\xc0\xde\x88\x80C\xc0\x11\xa0\rh\xc9\\nf]\x97\xb2\x91\x06\xe0\x1f\x01\xbf\xaf\xff\xfc\x8c\x00\x9a\x00\x00\x00\x00IEND\xaeB`\x82"

FORM_DATA = (
    b"--"
    + BOUNDARY
    + CRLF
    + b'Content-Disposition: form-data; name="name"'
    + CRLF * 2
    + b"Name"
    + CRLF
    + b"--"
    + BOUNDARY
    + CRLF
    + b'Content-Disposition: form-data; name="username"'
    + CRLF * 2
    + b"Username"
    + CRLF
    + b"--"
    + BOUNDARY
    + CRLF
    + b'Content-Disposition: form-data; name="photo"; filename="py.png"'
    + CRLF
    + b"Content-Type: image/png"
    + CRLF * 2
    + FILE_DATA
    + CRLF
    + b"--"
    + BOUNDARY
    + CRLF
    + b'Content-Disposition: form-data; name="email"'
    + CRLF * 2
    + b"email@email.com"
    + CRLF
    + b"--"
    + BOUNDARY
    + CRLF
    + b'Content-Disposition: form-data; name="file"; filename="py.png"'
    + CRLF
    + b"Content-Type: image/png"
    + CRLF * 2
    + FILE_DATA
    + CRLF
    + b"--"
    + BOUNDARY
    + b"--"
    + CRLF
)

NO_FILE_FORM_DATA = (
    b"--"
    + BOUNDARY
    + CRLF
    + b'Content-Disposition: form-data; name="name"'
    + CRLF * 2
    + b"Name"
    + CRLF
    + b"--"
    + BOUNDARY
    + CRLF
    + b'Content-Disposition: form-data; name="username"'
    + CRLF * 2
    + b"Username"
    + CRLF
    + b"--"
    + BOUNDARY
    + CRLF
    + b'Content-Disposition: form-data; name="email"'
    + CRLF * 2
    + b"email@email.com"
    + CRLF
    + b"--"
    + BOUNDARY
    + b"--"
    + CRLF
)

HEADERS = Headers(
    [
        (
            b"content-type",
            b"multipart/form-data; boundary=" + BOUNDARY,
        )
    ]
)


async def _form_data():
    yield FORM_DATA


async def _form_split_boundary():
    for i in [FORM_DATA[:991], FORM_DATA[991:]]:
        yield i


async def _form_split_first_file():
    for i in [FORM_DATA[:500], FORM_DATA[500:]]:
        yield i


async def _form_split_second_file():
    for i in [FORM_DATA[:1500], FORM_DATA[1500:]]:
        yield i


async def _form_split_file_chunk():
    for i in range(0, len(FORM_DATA), 100):
        yield FORM_DATA[i : i + 100]


async def _form_split_file_chunk_uneven():
    for i in [
        FORM_DATA[:100],
        FORM_DATA[100:200],
        FORM_DATA[200:300],
        FORM_DATA[300:500],
        FORM_DATA[500:1000],
        FORM_DATA[1000:1500],
        FORM_DATA[1500:],
    ]:
        yield i


async def _no_file_form():
    yield NO_FILE_FORM_DATA


async def _save_file(source: multipart.File, dest: Path):
    def __save_file():
        with open(dest, "wb") as fd:
            fd.write(source.file_object.read())

    await asyncio.to_thread(__save_file)


@pytest.mark.parametrize(
    "uploaded_file_data",
    [
        _form_data(),
        _form_split_boundary(),
        _form_split_first_file(),
        _form_split_second_file(),
        _form_split_file_chunk(),
        _form_split_file_chunk_uneven(),
    ],
    ids=[
        "unsplit",
        "boundary split",
        "first file split",
        "second file split",
        "file chunk",
        "file chunk uneven",
    ],
)
async def test_request_upload(uploaded_file_data, tmp_path: Path):
    scope = {
        "type": "http",
        "headers": [
            (b"content-type", b"multipart/form-data; boundary=" + BOUNDARY),
            (b"content-length", str(len(FORM_DATA)).encode("latin-1")),
        ],
    }

    receive = await asgi_receive_from_stream(uploaded_file_data)
    request = Request(scope, receive, None)

    result = await read_form(request)

    uploaded_file = result["photo"]
    file_destination = tmp_path / f"photo-{uploaded_file.file_name}"

    await _save_file(uploaded_file, file_destination)

    uploaded_file_data = file_destination.read_bytes()
    assert uploaded_file_data == FILE_DATA

    uploaded_file = result["file"]
    file_destination = tmp_path / f"file-{uploaded_file.file_name}"

    await _save_file(uploaded_file, file_destination)

    uploaded_file_data = file_destination.read_bytes()
    assert uploaded_file_data == FILE_DATA


async def test_no_file_form():
    scope = {
        "type": "http",
        "headers": [
            (b"content-type", b"multipart/form-data; boundary=" + BOUNDARY),
            (b"content-length", str(len(NO_FILE_FORM_DATA)).encode("latin-1")),
        ],
    }

    receive = await asgi_receive_from_stream(_no_file_form())
    request = Request(scope, receive, None)

    result = await read_form(request)
    expected = {
        "name": "Name",
        "username": "Username",
        "email": "email@email.com",
    }
    assert result == expected
