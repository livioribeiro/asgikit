import pytest

from asgikit.util.multi_value_dict import MultiStrValueDict


@pytest.mark.parametrize(
    "initial",
    [
        [("a", "1"), ("b", ["2", "3"])],
        {"a": "1", "b": ["2", "3"]},
        [("a", 1), ("b", [2, 3])],
        {"a": 1, "b": [2, 3]},
    ],
    ids=["str list", "str dict", "non str list", "non str dict"],
)
def test_initial_data(initial):
    d = MultiStrValueDict(initial)
    assert d.data == {"a": ["1"], "b": ["2", "3"]}


testdata_single = [
    ("1", "2"),
    (1, "2"),
    ("1", 2),
    (1, 2),
]


@pytest.mark.parametrize("data1,data2", testdata_single)
def test_add_single_value(data1, data2):
    d = MultiStrValueDict()

    d.add("a", data1)
    assert d.data == {"a": ["1"]}

    d.add("a", data2)
    assert d.data == {"a": ["1", "2"]}


@pytest.mark.parametrize("data1,data2", testdata_single)
def test_set_single_value(data1, data2):
    d = MultiStrValueDict()

    d.set("a", data1)
    assert d.data == {"a": ["1"]}

    d.set("a", data2)
    assert d.data == {"a": ["2"]}


@pytest.mark.parametrize("data1,data2", testdata_single)
def test_setitem_single_value(data1, data2):
    d = MultiStrValueDict()

    d["a"] = data1
    assert d.data == {"a": ["1"]}

    d["a"] = data2
    assert d.data == {"a": ["2"]}


testdata_list = [
    (["1", "2"], ["3", "4"]),
    ([1, "2"], [3, "4"]),
    (["1", 2], ["3", 4]),
    ([1, 2], [3, 4]),
]


@pytest.mark.parametrize("data1,data2", testdata_list)
def test_add_list(data1, data2):
    d = MultiStrValueDict()

    d.add("a", data1)
    assert d.data == {"a": ["1", "2"]}

    d.add("a", data2)
    assert d.data == {"a": ["1", "2", "3", "4"]}


@pytest.mark.parametrize("data1,data2", testdata_list)
def test_set_list(data1, data2):
    d = MultiStrValueDict()

    d.set("a", data1)
    assert d.data == {"a": ["1", "2"]}

    d.set("a", data2)
    assert d.data == {"a": ["3", "4"]}


@pytest.mark.parametrize("data1,data2", testdata_list)
def test_setitem_list(data1, data2):
    d = MultiStrValueDict()

    d["a"] = data1
    assert d.data == {"a": ["1", "2"]}

    d["a"] = data2
    assert d.data == {"a": ["3", "4"]}
