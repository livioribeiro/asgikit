from ward import test

from asgikit.headers import MutableHeaders


@test("init")
def _():
    h = MutableHeaders({"a": "1", "b": [2, 3]})
    assert h.data == {"a": ["1"], "b": ["2", "3"]}


@test("encode")
def _():
    h = MutableHeaders({"a": "1", "b": [2, 3]})
    assert h.encode() == [(b"a", b"1"), (b"b", b"2, 3")]