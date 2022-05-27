from asgikit.headers import MutableHeaders


def test_init_from_dict():
    h = MutableHeaders({"a": "1", "b": [2, 3]})
    assert h.data == {"a": ["1"], "b": ["2", "3"]}


def test_init_from_list():
    h = MutableHeaders([("a", "1"), ("b", [2, 3])])
    assert h.data == {"a": ["1"], "b": ["2", "3"]}


def test_encode():
    h = MutableHeaders({"a": "1", "b": [2, 3]})
    assert h.encode() == [(b"a", b"1"), (b"b", b"2, 3")]
