import pytest

from asgikit.util.multi_value_dict import MultiValueDict


@pytest.mark.parametrize(
    "initial",
    [
        [("a", 1), ("b", 2)],
        {"a": 1, "b": 2},
    ],
    ids=["list", "dict"],
)
def test_initial_data(initial):
    d = MultiValueDict(initial)
    assert d.data == {"a": [1], "b": [2]}


def test_add_single_value():
    d = MultiValueDict()

    d.add("a", 1)
    assert d.data == {"a": [1]}

    d.add("a", 2)
    assert d.data == {"a": [1, 2]}


def test_set_single_value():
    d = MultiValueDict()

    d.set("a", 1)
    assert d.data == {"a": [1]}

    d.set("a", 2)
    assert d.data == {"a": [2]}


def test_add_list():
    d = MultiValueDict()

    d.add("a", [1, 2])
    assert d.data == {"a": [1, 2]}

    d.add("a", [3, 4])
    assert d.data == {"a": [1, 2, 3, 4]}


def test_set_list():
    d = MultiValueDict()

    d.set("a", [1, 2])
    assert d.data == {"a": [1, 2]}

    d.set("a", [3, 4])
    assert d.data == {"a": [3, 4]}


def test_setitem_single_value():
    d = MultiValueDict()

    d["a"] = 1
    assert d.data == {"a": [1]}

    d["a"] = 2
    assert d.data == {"a": [2]}


def test_setitem_list():
    d = MultiValueDict()

    d["a"] = [1, 2]
    assert d.data == {"a": [1, 2]}

    d["a"] = [3, 4]
    assert d.data == {"a": [3, 4]}


def test_get_first():
    d = MultiValueDict()
    d["a"] = [1, 2]
    assert d.get("a") == 1


def test_get_all():
    d = MultiValueDict()
    d["a"] = [1, 2]
    assert d.get_all("a") == [1, 2]


def test_getitem():
    d = MultiValueDict()
    d["a"] = [1, 2]
    assert d["a"] == [1, 2]
