import pytest
from asgiref.typing import HTTPDisconnectEvent, HTTPRequestEvent, HTTPScope

from asgikit.errors.http import ClientDisconnectError
from asgikit.requests import HttpMethod, HttpRequest


def test_http_method_compare_with_str():
    assert HttpMethod.GET == "GET"
    assert HttpMethod.POST == "POST"
    assert HttpMethod.PUT == "PUT"
    assert HttpMethod.PATCH == "PATCH"
    assert HttpMethod.DELETE == "DELETE"
    assert HttpMethod.OPTIONS == "OPTIONS"


def test_http_method_into_str():
    assert str(HttpMethod.GET) == "GET"
    assert str(HttpMethod.POST) == "POST"
    assert str(HttpMethod.PUT) == "PUT"
    assert str(HttpMethod.PATCH) == "PATCH"
    assert str(HttpMethod.DELETE) == "DELETE"
    assert str(HttpMethod.OPTIONS) == "OPTIONS"


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
    request = HttpRequest(SCOPE, None, None)
    assert request.http_version == "1.1"
    assert request.method == HttpMethod.GET
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

    request = HttpRequest(SCOPE, receive, None)

    result = []
    async for data in request.stream():
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

    request = HttpRequest(SCOPE, receive, None)

    with pytest.raises(ClientDisconnectError):
        async for _ in request.stream():
            pass


async def test_request_body_single_chunk():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"12345",
            "more_body": False,
        }

    request = HttpRequest(SCOPE, receive, None)

    result = await request.body()
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

    request = HttpRequest(SCOPE, receive, None)

    result = await request.body()
    assert result == b"12345"


async def test_request_text():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"12345",
            "more_body": False,
        }

    request = HttpRequest(SCOPE, receive, None)

    result = await request.text()
    assert result == "12345"


async def test_request_json():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b'{"name": "Selva", "rank": 1}',
            "more_body": False,
        }

    request = HttpRequest(SCOPE, receive, None)

    result = await request.json()
    assert result == {"name": "Selva", "rank": 1}


async def test_request_invalid_json_should_fail():
    async def receive() -> HTTPRequestEvent:
        return {
            "type": "http.request",
            "body": b"name,rank\nSelva,1",
            "more_body": False,
        }

    request = HttpRequest(SCOPE, receive, None)

    with pytest.raises(ValueError):
        await request.json()


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
    request = HttpRequest(scope, receive, None)

    result = await request.form()
    assert result == expected
