from ward import test

from asgikit.multi_value_dict import MultiStrValueDict

for name, initial in [
    ("str list", [("a", "1"), ("b", ["2", "3"])]),
    ("str dict", {"a": "1", "b": ["2", "3"]}),
    ("non str list", [("a", 1), ("b", [2, 3])]),
    ("non str dict", {"a": 1, "b": [2, 3]}),
]:

    @test(f"initial data {name}")
    def _():
        d = MultiStrValueDict(initial)
        assert d.data == {"a": ["1"], "b": ["2", "3"]}


for data1, data2 in [
    ("1", "2"),
    (1, "2"),
    ("1", 2),
    (1, 2),
]:

    @test(f"add single value")
    def _(data1=data1, data2=data2):
        d = MultiStrValueDict()

        d.add("a", data1)
        assert d.data == {"a": ["1"]}

        d.add("a", data2)
        assert d.data == {"a": ["1", "2"]}

    @test("set single value")
    def _(data1=data1, data2=data2):
        d = MultiStrValueDict()

        d.set("a", data1)
        assert d.data == {"a": ["1"]}

        d.set("a", data2)
        assert d.data == {"a": ["2"]}

    @test("setitem single value")
    def _(data1=data1, data2=data2):
        d = MultiStrValueDict()

        d["a"] = data1
        assert d.data == {"a": ["1"]}

        d["a"] = data2
        assert d.data == {"a": ["2"]}


for data1, data2 in [
    (["1", "2"], ["3", "4"]),
    ([1, "2"], [3, "4"]),
    (["1", 2], ["3", 4]),
    ([1, 2], [3, 4]),
]:

    @test("add list")
    def _(data1=data1, data2=data2):
        d = MultiStrValueDict()

        d.add("a", data1)
        assert d.data == {"a": ["1", "2"]}

        d.add("a", data2)
        assert d.data == {"a": ["1", "2", "3", "4"]}

    @test("set list")
    def _(data1=data1, data2=data2):
        d = MultiStrValueDict()

        d.set("a", data1)
        assert d.data == {"a": ["1", "2"]}

        d.set("a", data2)
        assert d.data == {"a": ["3", "4"]}

    @test("setitem list")
    def _(data1=data1, data2=data2):
        d = MultiStrValueDict()

        d["a"] = data1
        assert d.data == {"a": ["1", "2"]}

        d["a"] = data2
        assert d.data == {"a": ["3", "4"]}
