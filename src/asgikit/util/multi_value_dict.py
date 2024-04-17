from collections import UserDict
from typing import Generic, Optional, TypeVar

__all__ = ("MultiValueDict", "MultiStrValueDict")

T = TypeVar("T")


class MultiValueDict(Generic[T], UserDict):
    def __init__(
        self,
        initial: dict[str, T | list[T]] | list[tuple[str, T | list[T]]] = None,
    ):
        super().__init__()

        if initial:
            iter_data = initial.items() if isinstance(initial, dict) else initial

            for key, value in iter_data:
                value_to_add = value if isinstance(value, list) else [value]
                self.add(key, value_to_add)

    def get(self, key: str, default: T = None) -> Optional[T]:
        return value[0] if (value := self.data.get(key)) else default

    def get_all(self, key: str, default: T = None) -> Optional[list[T]]:
        return self.data.get(key, default)

    def _add(self, key: str, value: T | list[T]):
        if isinstance(value, list):
            self.data[key] += value
        else:
            self.data[key].append(value)

    def add(self, key: str, value: T | list[T]):
        if key not in self:
            self.data[key] = []
        self._add(key, value)

    def set(self, key: str, value: T | list[T]):
        self.data[key] = []
        self._add(key, value)

    def __setitem__(self, key: str, value: T | list[T]):
        self.set(key, value)


class MultiStrValueDict(MultiValueDict[str]):
    def _add(self, key: str, value: str | list[str]):
        if isinstance(value, str):
            self.data[key].append(value)
        elif isinstance(value, list):
            if all(isinstance(i, str) for i in value):
                self.data[key] += value
            else:
                self.data[key] += [str(i) for i in value]
        else:
            self.data[key].append(str(value))
