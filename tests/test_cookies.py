from asgikit.cookies import parse_cookie
from asgikit.requests import Request


def test_parse_cookie():
    data = "key1=value1; key2=value2"
    result = parse_cookie(data)
    assert result == {"key1": "value1", "key2": "value2"}


def test_request_get_cookie():
    scope = {
        "type": "http",
        "headers": [
            (b"cookie", b"key1=value1; key2=value2"),
        ],
    }

    request = Request(scope, None, None)
    result = request.cookies
    assert result == {"key1": "value1", "key2": "value2"}
