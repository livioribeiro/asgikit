import pytest

from asgikit.headers import encode_headers, parse_headers


@pytest.mark.parametrize(
    "raw,parsed",
    [
        ([(b"a", b"1"), (b"b", b"2")], {"a": "1", "b": "2"}),
        ([(b"a", b"1, 2"), (b"b", b"3, 4")], {"a": "1, 2", "b": "3, 4"}),
        (
            [(b"a", b"1"), (b"a", b"2"), (b"b", b"3"), (b"b", b"4")],
            {"a": ["1", "2"], "b": ["3", "4"]},
        ),
        ([], {}),
    ],
)
def test_parse(raw, parsed):
    result = parse_headers(raw)
    assert result == parsed


@pytest.mark.parametrize(
    "parsed,encoded",
    [
        ({"a": "1", "b": "2"}, [(b"a", b"1"), (b"b", b"2")]),
        (
            {"a": ["1", "2"], "b": ["3", "4"]},
            [(b"a", b"1, 2"), (b"b", b"3, 4")],
        ),
        ({}, []),
    ],
)
def test_encode(parsed, encoded):
    result = encode_headers(parsed)
    assert result == encoded
