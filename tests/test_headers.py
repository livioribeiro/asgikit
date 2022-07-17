import pytest

from asgikit.headers import Headers


@pytest.mark.parametrize(
    "raw,parsed",
    [
        ([(b"a", b"1"), (b"b", b"2")], {"a": ["1"], "b": ["2"]}),
        ([(b"a", b"1, 2"), (b"b", b"3, 4")], {"a": ["1", "2"], "b": ["3", "4"]}),
        ([], {}),
    ],
)
def test_parse(raw, parsed):
    h = Headers(raw)
    assert h._parsed == parsed


def test_get_first():
    h = Headers([(b"a", b"1, 2")])
    assert h.get("a") == "1"


def test_get_all():
    h = Headers([(b"a", b"1, 2")])
    assert h.get_all("a") == ["1", "2"]


def test_getitem():
    h = Headers([(b"a", b"1, 2")])
    assert h["a"] == "1"


def test_get_raw():
    h = Headers([(b"a", b"1, 2")])
    assert h.get_raw(b"a") == b"1, 2"


def test_items():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.items()) == [("a", ["1"]), ("b", ["2", "3"])]


def test_keys():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.keys()) == ["a", "b"]


def test_values():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.values()) == [["1"], ["2", "3"]]


def test_items_raw():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.items_raw()) == [(b"a", b"1"), (b"b", b"2, 3")]


def test_keys_raw():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.keys_raw()) == [b"a", b"b"]


def test_values_raw():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.values_raw()) == [b"1", b"2, 3"]


def test_contains_with_str():
    h = Headers([(b"a", b"1"), (b"b", b"2")])
    assert "a" in h


@pytest.mark.parametrize(
    "data",
    [
        Headers([(b"a", b"1"), (b"b", b"2, 3")]),
        {"a": ["1"], "b": ["2", "3"]},
        [(b"a", b"1"), (b"b", b"2, 3")],
    ],
    ids=["Headers", "dict", "list"],
)
def test_equals(data):
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert data == h


def test_not_equals():
    h = Headers()
    assert h != object()
