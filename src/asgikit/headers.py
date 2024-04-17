from typing import Iterable, Optional

from asgikit.util.multi_value_dict import MultiStrValueDict

__all__ = ("Headers", "MutableHeaders")

DEFAULT_ENCODING = "utf-8"
HEADER_ENCODING = "latin-1"


class Headers:
    __slots__ = ("_raw", "_parsed")

    def __init__(
        self, raw: Iterable[tuple[bytes, bytes]] = None, encoding=DEFAULT_ENCODING
    ):
        self._raw: dict[bytes, bytes] = dict(raw) if raw else {}
        self._parsed: dict[str, list[str]] = {}

        if not raw:
            return

        for key_raw, value_raw in raw:
            key, value = key_raw.decode(encoding).lower(), value_raw.decode(encoding)
            self._parsed[key] = [i.strip() for i in value.split(",")]

    def get(self, key: str, default: str = None) -> Optional[str]:
        key = key.lower()
        return value[0] if (value := self._parsed.get(key)) else default

    def get_all(self, key: str, default: list[str] = None) -> Optional[list[str]]:
        key = key.lower()
        return self._parsed.get(key, default)

    def get_raw(self, key: bytes, default: bytes = None) -> Optional[bytes]:
        return self._raw.get(key, default)

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

    def __contains__(self, key: str) -> bool:
        key = key.lower()
        return key in self._parsed

    def __getitem__(self, key: str) -> str:
        key = key.lower()
        return self._parsed[key][0]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Headers):
            return self._raw == other._raw and self._parsed == other._parsed
        if isinstance(other, dict):
            return self._parsed == other
        if isinstance(other, list):
            return list(self._raw.items()) == other
        return False


class MutableHeaders(MultiStrValueDict):
    def __init__(
        self,
        initial: dict[str, str | list[str]] | list[tuple[str, str | list[str]]] = None,
    ):
        super().__init__(initial)

    def encode(self) -> list[tuple[bytes, bytes]]:
        return [
            (k.lower().encode(HEADER_ENCODING), ", ".join(v).encode(HEADER_ENCODING))
            for k, v in self.data.items()
        ]
