from collections import OrderedDict
from typing import Iterable, Optional

from asgikit.utils import MultiStrValueDict

DEFAULT_ENCODING = "utf-8"
HEADER_ENCODING = "latin-1"


class Headers:
    def __init__(
        self, raw: list[tuple[bytes, bytes]] = None, encoding=DEFAULT_ENCODING
    ):
        self._raw: dict[bytes, bytes] = OrderedDict(raw) if raw else {}
        self._parsed: dict[str, list[str]] = {}

        if not raw:
            return

        for key_raw, value_raw in raw:
            key, value = key_raw.decode(encoding), value_raw.decode(encoding)
            if key not in self:
                self._parsed[key] = []
            self._parsed[key] += [i.strip() for i in value.split(",")]

    def get_first(self, key: str, default: str = None) -> Optional[str]:
        return value[0] if (value := self._parsed.get(key)) else default

    def get_all(self, key: str, default: list[str] = None) -> Optional[list[str]]:
        return self._parsed.get(key, default)

    def get(self, key: str, default: list[str] = None) -> Optional[list[str]]:
        return self.get_all(key, default)

    def get_raw(self, key: str | bytes, default: bytes = None) -> Optional[bytes]:
        raw_key = key if isinstance(key, bytes) else key.encode(HEADER_ENCODING)
        return self._raw.get(raw_key, default)

    def items(self) -> Iterable[tuple[str, list[str]]]:
        return self._parsed.items()

    def keys(self) -> Iterable[str]:
        return self._parsed.keys()

    def values(self) -> Iterable[list[str]]:
        return self._parsed.values()

    def items_raw(self) -> Iterable[tuple[bytes, bytes]]:
        return self._raw.items()

    def keys_raw(self) -> Iterable[bytes]:
        return self._raw.keys()

    def values_raw(self) -> Iterable[bytes]:
        return self._raw.values()

    def __contains__(self, key: str | bytes) -> bool:
        return key in self._parsed if isinstance(key, str) else key in self._raw

    def __getitem__(self, key: str | bytes) -> bytes | list[str]:
        return self._parsed[key] if isinstance(key, str) else self._raw[key]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Headers):
            return self._raw == other._raw and self._parsed == other._parsed
        if isinstance(other, dict):
            return self._parsed == other
        if isinstance(other, list):
            return list(self._raw.items()) == other
        return False


class MutableHeaders(MultiStrValueDict):
    def __init__(self, initial: dict[str, str | list[str]] = None):
        super().__init__(initial)

    def encode(self) -> list[tuple[bytes, bytes]]:
        return [
            (k.lower().encode(HEADER_ENCODING), ", ".join(v).encode(HEADER_ENCODING))
            for k, v in self.data.items()
        ]
