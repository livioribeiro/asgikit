from collections import UserDict
from typing import Any, Optional, Union


class MultiValueDict(UserDict):
    def __init__(self, initial: dict[str, Union[Any, list[Any]]] = None):
        super().__init__()

        if initial:
            for k, v in initial.items():
                if isinstance(v, list):
                    self[k] = v
                else:
                    self[k] = [v]

    def get_first(self, key: str, default=None) -> Optional[Any]:
        return value[0] if (value := self.get(key)) else default

    def add(self, key: str, value: Union[Any, list[Any]]):
        if key not in self:
            self.data[key] = []

        if isinstance(value, str):
            self[key].append(value)
        elif isinstance(value, list):
            if all(isinstance(i, str) for i in value):
                self[key] += value
            else:
                self[key] += [str(i) for i in value]
        else:
            self[key].append(str(value))

    def put(self, key: str, value: Union[str, list[str]]):
        self.data[key] = []
        self.add(key, value)

    def __setitem__(self, key: str, value: Union[str, list[str]]):
        self.put(key, value)
