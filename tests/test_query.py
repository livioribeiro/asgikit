import pytest

from asgikit.query import Query

testdata = [
    (b"a=1", {"a": ["1"]}),
    (b"a=1&b=2", {"a": ["1"], "b": ["2"]}),
    (b"a=%C3%A1&b=%C3%BC", {"a": ["á"], "b": ["ü"]}),
    (b"a=1&a=2", {"a": ["1", "2"]}),
]

testdata_ids = ["single value", "simple values", "percent encoded", "multiple values"]


@pytest.mark.parametrize("query,expected", testdata, ids=testdata_ids)
def test_parse(query, expected):
    q = Query(query)
    assert q.data == expected


@pytest.mark.parametrize("query,data", testdata, ids=testdata_ids)
def test_encode(query, data):
    q = Query()
    q.update(data)
    assert q.encode() == query


def test_parse_str_should_fail():
    with pytest.raises(Exception):
        Query("a=1")


@pytest.mark.parametrize(
    "data",
    [
        Query(b"a=1&b=2&b=3"),
        {"a": ["1"], "b": ["2", "3"]},
        "a=1&b=2&b=3",
        b"a=1&b=2&b=3",
    ],
    ids=["Query", "dict", "str", "bytes"],
)
def test_equals(data):
    q = Query(b"a=1&b=2&b=3")
    assert data == q


def test_not_equals():
    q = Query()
    assert q != object()
