import copy
import importlib
import sys
from http import HTTPMethod

import pytest
from asgiref.typing import HTTPDisconnectEvent, HTTPRequestEvent, HTTPScope

from asgikit.errors.http import ClientDisconnectError
from asgikit.requests import Request, read_body, read_form, read_json, read_text

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
    assert request.cookie is None
    assert request.accept == "application/json"
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

    request = Request(copy.copy(SCOPE), receive, None)

    result = await read_body(request)
    assert result == b"12345"


async def test_request_text():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"12345",
            "more_body": False,
        }

    request = Request(copy.copy(SCOPE), receive, None)

    result = await read_text(request)
    assert result == "12345"


@pytest.mark.parametrize(
    "name, encoder",
    [
        ("json", None),
        ("orjson", "orjson"),
        ("orjson", "orjson.loads,orjson.dumps")
    ],
    ids=["json", "orjson", "orjson-direct"],
)
async def test_request_json(name, encoder, monkeypatch):
    if encoder:
        monkeypatch.setenv("ASGIKIT_JSON_ENCODER", encoder)

    importlib.reload(sys.modules["asgikit._json"])
    from asgikit._json import JSON_DECODER

    assert JSON_DECODER.__module__.startswith(name)

    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b'{"name": "Selva", "rank": 1}',
            "more_body": False,
        }

    request = Request(copy.copy(SCOPE), receive, None)

    result = await read_json(request)
    assert result == {"name": "Selva", "rank": 1}


@pytest.mark.parametrize("encoder", ["invalid", "module.invalid"])
def test_json_invalid_decoder_should_fail(encoder, monkeypatch):
    monkeypatch.setenv("ASGIKIT_JSON_ENCODER", encoder)
    with pytest.raises(ValueError, match=f"Invalid ASGIKIT_JSON_ENCODER: {encoder}"):
        importlib.reload(sys.modules["asgikit._json"])


async def test_request_invalid_json_should_fail():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"name,rank\nSelva,1",
            "more_body": False,
        }

    request = Request(copy.copy(SCOPE), receive, None)

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


async def test_request_wrap_asgi():
    async def receive() -> dict:
        return {}

    async def send(_: dict):
        pass

    send_event = {}

    request = Request(copy.copy(SCOPE), receive, send)

    assert await request.asgi_receive() == {}
    await request.asgi_send(send_event)
    assert send_event == {}

    async def new_receive(orig_receive) -> dict:
        event = await orig_receive()
        return event | {"wrapped": True}

    async def new_send(orig_send, event: dict):
        event["wrapped"] = True
        await orig_send(event)

    request.wrap_asgi(receive=new_receive, send=new_send)

    assert await request.asgi_receive() == {"wrapped": True}
    await request.asgi_send(send_event)
    assert send_event == {"wrapped": True}


async def test_request_response_wrap_asgi():
    async def receive() -> dict:
        return {}

    async def send(_: dict):
        pass

    send_event = {}

    request = Request(copy.copy(SCOPE), receive, send)
    response = request.response

    assert await response._receive() == {}
    await response._send(send_event)
    assert send_event == {}

    async def new_receive(orig_receive) -> dict:
        event = await orig_receive()
        return event | {"wrapped": True}

    async def new_send(orig_send, event: dict):
        event["wrapped"] = True
        await orig_send(event)

    request.wrap_asgi(receive=new_receive, send=new_send)

    assert await response._receive() == {"wrapped": True}
    await response._send(send_event)
    assert send_event == {"wrapped": True}


async def test_request_websocket_wrap_asgi():
    async def receive() -> dict:
        return {}

    async def send(_: dict):
        pass

    send_event = {}

    request = Request(copy.copy(SCOPE) | {"type": "websocket"}, receive, send)
    websocket = request.websocket

    assert await websocket._receive() == {}
    await websocket._send(send_event)
    assert send_event == {}

    async def new_receive(orig_receive) -> dict:
        event = await orig_receive()
        return event | {"wrapped": True}

    async def new_send(orig_send, event: dict):
        event["wrapped"] = True
        await orig_send(event)

    request.wrap_asgi(receive=new_receive, send=new_send)

    assert await websocket._receive() == {"wrapped": True}
    await websocket._send(send_event)
    assert send_event == {"wrapped": True}


@pytest.mark.parametrize(
    "content_type",
    [
        b"text/plain; charset=\"latin-1\"",
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
    result = await read_text(request)
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
    result = await read_text(request, encoding="latin-1")
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
        await read_text(request)


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
    result = await read_text(request, encoding="latin-1")
    assert result != data
