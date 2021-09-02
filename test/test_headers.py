from ward import test

from asgikit.headers import Headers

for raw, parsed in [
    ([(b"a", b"1"), (b"b", b"2")], {"a": ["1"], "b": ["2"]}),
    ([(b"a", b"1, 2"), (b"b", b"3, 4")], {"a": ["1", "2"], "b": ["3", "4"]}),
]:
    @test("parse")
    def _():
        h = Headers(raw)
        assert h._parsed == parsed
