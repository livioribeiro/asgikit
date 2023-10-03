from http import HTTPMethod

import pytest
from asgiref.typing import HTTPDisconnectEvent, HTTPRequestEvent, HTTPScope

from asgikit.errors.http import ClientDisconnectError
from asgikit.requests import (
    ATTRIBUTES_KEY,
    Request,
    read_body,
    read_form,
    read_json,
    read_text,
)

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
    request = Request(SCOPE, None, None)
    assert request.http_version == "1.1"
    assert request.method == HTTPMethod.GET
    assert request.path == "/"
    assert request.cookie is None
    assert request.accept == ["application/json"]
    assert request.content_type == "application/xml"
    assert request.content_length == 1024


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

    request = Request(SCOPE, receive, None)

    result = []
    async for data in request:
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

    request = Request(SCOPE, receive, None)

    with pytest.raises(ClientDisconnectError):
        async for _ in request:
            pass


async def test_request_body_single_chunk():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"12345",
            "more_body": False,
        }

    request = Request(SCOPE, receive, None)

    result = await read_body(request)
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

    request = Request(SCOPE, receive, None)

    result = await read_body(request)
    assert result == b"12345"


async def test_request_text():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"12345",
            "more_body": False,
        }

    request = Request(SCOPE, receive, None)

    result = await read_text(request)
    assert result == "12345"


async def test_request_json():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b'{"name": "Selva", "rank": 1}',
            "more_body": False,
        }

    request = Request(SCOPE, receive, None)

    result = await read_json(request)
    assert result == {"name": "Selva", "rank": 1}


async def test_request_invalid_json_should_fail():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"name,rank\nSelva,1",
            "more_body": False,
        }

    request = Request(SCOPE, receive, None)

    with pytest.raises(ValueError):
        await read_json(request)


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

    result = await read_form(request)
    assert result == expected


def test_request_attributes():
    request = Request(SCOPE, None, None)
    assert ATTRIBUTES_KEY in request._asgi.scope

    request["key"] = "value"
    assert request.attributes == {"key": "value"}


def test_request_edit_attributes():
    request = Request(SCOPE, None, None)
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
