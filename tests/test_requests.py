from asgikit.requests import HttpMethod


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
