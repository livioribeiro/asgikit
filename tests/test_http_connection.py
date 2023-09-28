from asgiref.typing import HTTPScope

from asgikit.headers import Headers
from asgikit.http import HttpConnection
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
