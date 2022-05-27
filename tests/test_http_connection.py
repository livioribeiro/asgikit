from asgikit.headers import Headers
from asgikit.http_connection import HttpConnection
from asgikit.query import Query


def test_init():
    scope = {
        "type": "http",
        "asgi": {
            "version": "3.0",
            "spec_version": "2.3",
        },
        "scheme": "http",
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 9000),
        "path": "/path",
        "raw_path": b"/path",
        "root_path": "",
        "query_string": b"a=1&b=2",
        "headers": [
            (b"a", b"1"),
            (b"b", b"2, 3"),
        ],
    }

    def receive():
        return {}

    def send(_):
        pass

    connection = HttpConnection(scope, receive, send)

    expected_query = Query(b"a=1&b=2")
    expected_headers = Headers(
        [
            (b"a", b"1"),
            (b"b", b"2, 3"),
        ]
    )
    assert connection.query == expected_query
    assert connection.headers == expected_headers
