from ward import test

from asgikit.multi_value_dict import MultiValueDict

for name, initial in [
    ("list", [("a", 1), ("b", 2)]),
    ("dict", {"a": 1, "b": 2}),
]:

    @test(f"initial data {name}")
    def _():
        d = MultiValueDict(initial)
        assert d.data == {"a": [1], "b": [2]}


@test("add single value")
def _():
    d = MultiValueDict()

    d.add("a", 1)
    assert d.data == {"a": [1]}

    d.add("a", 2)
    assert d.data == {"a": [1, 2]}


@test("set single value")
def _():
    d = MultiValueDict()

    d.set("a", 1)
    assert d.data == {"a": [1]}

    d.set("a", 2)
    assert d.data == {"a": [2]}


@test("add list")
def _():
    d = MultiValueDict()

    d.add("a", [1, 2])
    assert d.data == {"a": [1, 2]}

    d.add("a", [3, 4])
    assert d.data == {"a": [1, 2, 3, 4]}


@test("set list")
def _():
    d = MultiValueDict()

    d.set("a", [1, 2])
    assert d.data == {"a": [1, 2]}

    d.set("a", [3, 4])
    assert d.data == {"a": [3, 4]}


@test("setitem single value")
def _():
    d = MultiValueDict()

    d["a"] = 1
    assert d.data == {"a": [1]}

    d["a"] = 2
    assert d.data == {"a": [2]}


@test("setitem list")
def _():
    d = MultiValueDict()

    d["a"] = [1, 2]
    assert d.data == {"a": [1, 2]}

    d["a"] = [3, 4]
    assert d.data == {"a": [3, 4]}


@test("get first")
def _():
    d = MultiValueDict()
    d["a"] = [1, 2]
    assert d.get_first("a") == 1


@test("get all")
def _():
    d = MultiValueDict()
    d["a"] = [1, 2]
    assert d.get_all("a") == [1, 2]


@test("getitem")
def _():
    d = MultiValueDict()
    d["a"] = [1, 2]
    assert d["a"] == [1, 2]
