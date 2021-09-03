import ward
from ward import test

from asgikit.query import Query

for tag, query, data in [
    ("single value", b"a=1", {"a": ["1"]}),
    ("simple values", b"a=1&b=2", {"a": ["1"], "b": ["2"]}),
    ("percent encoded", b"a=%C3%A1&b=%C3%BC", {"a": ["á"], "b": ["ü"]}),
    ("multiple values", b"a=1&a=2", {"a": ["1", "2"]}),
]:

    @test(f"parse {tag}")
    def _(query=query, data=data):
        q = Query(query)
        assert q.data == data

    @test(f"encode {tag}")
    def _(query=query, data=data):
        q = Query()
        q.update(data)
        assert q.encode() == query


@test("parse str should fail")
def _():
    with ward.raises(Exception):
        Query("a=1")


for tag, data in [
    ("Query", Query(b"a=1&b=2&b=3")),
    ("dict", {"a": ["1"], "b": ["2", "3"]}),
    ("str", "a=1&b=2&b=3"),
    ("bytes", b"a=1&b=2&b=3"),
]:

    @test(f"equals {tag}")
    def _(data=data):
        q = Query(b"a=1&b=2&b=3")
        assert data == q


@test("not equals")
def _():
    q = Query()
    assert q != object()
