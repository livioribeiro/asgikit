from asgiref.typing import HTTPScope

from asgikit.headers import Headers
from asgikit.http_connection import HttpConnection
from asgikit.query import Query

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
    "query_string": b"a=1&b=2",
    "root_path": "",
    "headers": [
        (b"a", b"1"),
        (b"b", b"2, 3"),
    ],
    "client": None,
    "server": None,
    "extensions": None,
}


def test_init():
    connection = HttpConnection(SCOPE, None, None)

    expected_query = Query(b"a=1&b=2")
    expected_headers = Headers(
        [
            (b"a", b"1"),
            (b"b", b"2, 3"),
        ]
    )
    assert connection.query == expected_query
    assert connection.headers == expected_headers


def test_request_attributes():
    request = HttpConnection(SCOPE, None, None)
    assert "attributes" in request._context.scope

    request["key"] = "value"
    assert request.attibutes == {"key": "value"}


def test_request_edit_attributes():
    request = HttpConnection(SCOPE, None, None)
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
