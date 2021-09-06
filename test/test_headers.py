from ward import test

from asgikit.headers import Headers

for raw, parsed in [
    ([(b"a", b"1"), (b"b", b"2")], {"a": ["1"], "b": ["2"]}),
    ([(b"a", b"1, 2"), (b"b", b"3, 4")], {"a": ["1", "2"], "b": ["3", "4"]}),
    ([], {}),
]:

    @test("parse")
    def _():
        h = Headers(raw)
        assert h._parsed == parsed


@test("get first")
def _():
    h = Headers([(b"a", b"1, 2")])
    assert h.get_first("a") == "1"


@test("get all")
def _():
    h = Headers([(b"a", b"1, 2")])
    assert h.get_all("a") == ["1", "2"]
    assert h.get("a") == ["1", "2"]


@test("getitem")
def _():
    h = Headers([(b"a", b"1, 2")])
    assert h["a"] == ["1", "2"]


@test("get raw")
def _():
    h = Headers([(b"a", b"1, 2")])
    assert h.get_raw(b"a") == b"1, 2"


@test("get raw str key")
def _():
    h = Headers([(b"a", b"1, 2")])
    assert h.get_raw("a") == b"1, 2"


@test("items")
def _():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.items()) == [("a", ["1"]), ("b", ["2", "3"])]


@test("keys")
def _():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.keys()) == ["a", "b"]


@test("values")
def _():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.values()) == [["1"], ["2", "3"]]


@test("items raw")
def _():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.items_raw()) == [(b"a", b"1"), (b"b", b"2, 3")]


@test("keys raw")
def _():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.keys_raw()) == [b"a", b"b"]


@test("values raw")
def _():
    h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
    assert list(h.values_raw()) == [b"1", b"2, 3"]


@test("contains with str")
def _():
    h = Headers([(b"a", b"1"), (b"b", b"2")])
    assert "a" in h


@test("contains with bytes")
def _():
    h = Headers([(b"a", b"1"), (b"b", b"2")])
    assert b"a" in h


for name, data in [
    ("Headers", Headers([(b"a", b"1"), (b"b", b"2, 3")])),
    ("dict", {"a": ["1"], "b": ["2", "3"]}),
    ("list", [(b"a", b"1"), (b"b", b"2, 3")]),
]:

    @test(f"equals {name}")
    def _(data=data):
        h = Headers([(b"a", b"1"), (b"b", b"2, 3")])
        assert data == h


@test("not equals")
def _():
    h = Headers()
    assert h != object()
