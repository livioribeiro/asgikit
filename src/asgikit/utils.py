from collections import UserDict
from typing import Dict, Generic, List, Optional, Tuple, TypeVar

T = TypeVar("T")


class MultiValueDict(Generic[T], UserDict):
    def __init__(
        self,
        initial: List[Tuple[str, T | List[T]]] | Dict[str, T | List[T]] = None,
    ):
        super().__init__()

        if initial:
            iter_data = initial.items() if isinstance(initial, dict) else initial

            for key, value in iter_data:
                value_to_add = value if isinstance(value, list) else [value]
                self.add(key, value_to_add)

    def get_first(self, key: str, default: T = None) -> Optional[T]:
        return value[0] if (value := self.get(key)) else default

    def get_all(self, key: str, default: T = None) -> Optional[List[T]]:
        return self.data.get(key, default)

    def _add(self, key: str, value: T | List[T]):
        if isinstance(value, list):
            self.data[key] += value
        else:
            self.data[key].append(value)

    def add(self, key: str, value: T | List[T]):
        if key not in self:
            self.data[key] = []
        self._add(key, value)

    def set(self, key: str, value: T | List[T]):
        self.data[key] = []
        self._add(key, value)

    def __setitem__(self, key: str, value: T | List[T]):
        self.set(key, value)


class MultiStrValueDict(MultiValueDict[str]):
    def _add(self, key: str, value: str | List[str]):
        if isinstance(value, str):
            self.data[key].append(value)
        elif isinstance(value, list):
            if all(isinstance(i, str) for i in value):
                self.data[key] += value
            else:
                self.data[key] += [str(i) for i in value]
        else:
            self.data[key].append(str(value))
