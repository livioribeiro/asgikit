from asgikit.requests import HttpRequest, _parse_cookie


def test_parse_cookie():
    data = "key1=value1; key2=value2"
    result = _parse_cookie(data)
    assert result == {"key1": "value1", "key2": "value2"}


def test_request_get_cookie():
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "headers": [
            (b"cookie", b"key1=value1; key2=value2"),
        ]
    }

    request = HttpRequest(scope, None, None)
    result = request.cookie
    assert result == {"key1": "value1", "key2": "value2"}
