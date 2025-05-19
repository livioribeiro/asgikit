import copy
import importlib
import sys
from http import HTTPMethod

import pytest
from asgiref.typing import HTTPDisconnectEvent, HTTPRequestEvent, HTTPScope

from asgikit.errors.http import ClientDisconnectError
from asgikit.requests import Request

SCOPE: HTTPScope = {
    "asgi": {
        "version": "3.0",
        "spec_version": "2.3",
    },
    "type": "http",
    "http_version": "1.1",
    "method": "GET",
    "scheme": "http",
    "path": "/",
    "raw_path": b"/",
    "query_string": b"",
    "root_path": "",
    "headers": [
        (b"accept", b"application/json"),
        (b"content-type", b"application/xml"),
        (b"content-length", b"1024"),
    ],
    "client": None,
    "server": None,
    "extensions": None,
}


async def test_request_properties():
    request = Request(copy.copy(SCOPE), None, None)
    assert request.http_version == "1.1"
    assert request.method == HTTPMethod.GET
    assert request.path == "/"
    assert request.cookies == {}
    assert request.body.content_type == "application/xml"
    assert request.body.content_length == 1024


async def test_request_stream():
    num = 1

    async def receive() -> HTTPRequestEvent:
        nonlocal num
        event = {
            "type": "http.request",
            "body": f"{num}".encode(),
            "more_body": (num < 5),
        }
        num += 1
        return event

    request = Request(copy.copy(SCOPE), receive, None)

    result = []
    async for data in request.body:
        result.append(data)

    assert result == [b"1", b"2", b"3", b"4", b"5"]


async def test_request_stream_client_disconnect():
    sent = False

    async def receive() -> HTTPRequestEvent | HTTPDisconnectEvent:
        nonlocal sent
        if not sent:
            sent = True
            event: HTTPRequestEvent = {
                "type": "http.request",
                "body": b"12345",
                "more_body": True,
            }
        else:
            event: HTTPDisconnectEvent = {"type": "http.disconnect"}
        return event

    request = Request(copy.copy(SCOPE), receive, None)

    with pytest.raises(ClientDisconnectError):
        async for _ in request.body:
            pass


async def test_request_body_single_chunk():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"12345",
            "more_body": False,
        }

    request = Request(copy.copy(SCOPE), receive, None)

    result = await request.body.bytes()
    assert result == b"12345"


async def test_request_body_multiple_chunk():
    num = 1

    async def receive() -> HTTPRequestEvent:
        nonlocal num
        event = {
            "type": "http.request",
            "body": f"{num}".encode(),
            "more_body": (num < 5),
        }
        num += 1
        return event

    request = Request(copy.copy(SCOPE), receive, None)

    result = await request.body.bytes()
    assert result == b"12345"


async def test_request_text():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"12345",
            "more_body": False,
        }

    request = Request(copy.copy(SCOPE), receive, None)

    result = await request.body.text()
    assert result == "12345"


@pytest.mark.parametrize(
    "data,expected",
    [
        (b"name=a&value=1", {"name": "a", "value": "1"}),
        (b"name=a&name=b&value=1&value=2", {"name": ["a", "b"], "value": ["1", "2"]}),
        (b"name=a&value=1&value=2", {"name": "a", "value": ["1", "2"]}),
    ],
    ids=[
        "single values",
        "multiple values",
        "mixed",
    ],
)
async def test_request_form(data: bytes, expected: dict):
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": data,
            "more_body": False,
        }

    scope = SCOPE | {"headers": [(b"content-type", b"application/x-www-urlencoded")]}
    request = Request(scope, receive, None)

    result = await request.body.form()
    assert result == expected


def test_request_attributes():
    request = Request(copy.copy(SCOPE), None, None)

    request["key"] = "value"
    assert request.attributes == {"key": "value"}


def test_request_edit_attributes():
    request = Request(copy.copy(SCOPE), None, None)
    request["str"] = "value"
    request["int"] = 1

    assert "str" in request
    assert request["str"] == "value"

    assert "int" in request
    assert request["int"] == 1

    del request["str"]
    del request["int"]

    assert "str" not in request
    assert "int" not in request


@pytest.mark.parametrize(
    "content_type",
    [
        b'text/plain; charset="latin-1"',
        b"text/plain; charset=latin-1",
    ],
    ids=[
        "with quotes",
        "without quotes",
    ],
)
async def test_read_text_charset(content_type):
    data = "¶"
    encoded_data = data.encode("latin-1")

    scope = copy.copy(SCOPE)
    scope["headers"] = [
        (b"content-type", content_type),
        (b"content-length", str(len(encoded_data)).encode()),
    ]

    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": encoded_data,
            "more_body": False,
        }

    request = Request(scope, receive, None)
    result = await request.body.text()
    assert result == data


async def test_read_text_with_given_charset():
    data = "¶"
    encoded_data = data.encode("latin-1")

    scope = copy.copy(SCOPE)
    scope["headers"] = [
        (b"content-type", b"text/plain"),
        (b"content-length", str(len(encoded_data)).encode()),
    ]

    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": encoded_data,
            "more_body": False,
        }

    request = Request(scope, receive, None)
    result = await request.body.text(encoding="latin-1")
    assert result == data


async def test_read_text_invalid_utf_8_charset_should_fail():
    data = "¶"
    encoded_data = data.encode("latin-1")

    scope = copy.copy(SCOPE)
    scope["headers"] = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"content-length", str(len(encoded_data)).encode()),
    ]

    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": encoded_data,
            "more_body": False,
        }

    request = Request(scope, receive, None)
    with pytest.raises(UnicodeDecodeError):
        await request.body.text()


async def test_read_text_invalid_given_charset_should_fail():
    data = "¶"
    encoded_data = data.encode("utf-8")

    scope = copy.copy(SCOPE)
    scope["headers"] = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(encoded_data)).encode()),
    ]

    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": encoded_data,
            "more_body": False,
        }

    request = Request(scope, receive, None)
    result = await request.body.text(encoding="latin-1")
    assert result != data
