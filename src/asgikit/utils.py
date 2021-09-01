from collections import UserDict
from collections.abc import Iterable
from typing import Any, Optional, Union


class MultiValueDict(UserDict):
    def __init__(self, initial: Union[list[tuple[str, Any], dict[str, Any]]] = None):
        super().__init__()

        if initial:
            if hasattr(initial, "items"):
                iter = initial.items()
            else:
                iter = initial
            for k, v in iter:
                self.add(k, v)

    def get_first(self, key: str, default=None) -> Optional[Any]:
        return value[0] if (value := self.get(key)) else default

    def get_all(self, key: str, default=None) -> Optional[list[Any]]:
        return self.data.get(key, default)

    def _add(self, key: str, value: Union[Any, list[Any]]):
        if isinstance(value, str):
            self.data[key].append(value)
        elif isinstance(value, list):
            if all(isinstance(i, str) for i in value):
                self.data[key] += value
            else:
                self.data[key] += [str(i) for i in value]
        else:
            self.data[key].append(str(value))

    def add(self, key: str, value: Union[Any, list[Any]]):
        if key not in self:
            self.data[key] = []
        self._add(key, value)

    def put(self, key: str, value: Union[str, list[str]]):
        self.data[key] = []
        self._add(key, value)

    def __setitem__(self, key: str, value: Union[str, list[str]]):
        self.put(key, value)
