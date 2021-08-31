from typing import Iterable, Optional, Union

from asgikit.utils import MultiValueDict

DEFAULT_ENCODING = "utf-8"
HEADER_CHARSET = "latin-1"


class Headers:
    def __init__(
        self, raw: list[tuple[bytes, bytes]] = None, encoding=DEFAULT_ENCODING
    ):
        self._raw = dict(raw) if raw else {}
        self._parsed = {}

        if not raw:
            return

        for key, value in raw:
            key, value = key.decode(encoding), value.decode(encoding)
            if key not in self:
                self._parsed[key] = []
            self._parsed[key] += [i.strip() for i in value.split(",")]

    def get_first(self, key: str, default: str = None) -> Optional[str]:
        return value[0] if (value := self._parsed.get(key)) else default

    def get(self, key: str, default: list[str] = None) -> Optional[list[str]]:
        return self._parsed.get(key, default)

    def get_raw(self, key: Union[str, bytes], default: bytes = None) -> Optional[bytes]:
        raw_key = key if isinstance(key, bytes) else key.encode("latin-1")
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

    def values_raw(self) -> Iterable[list[bytes]]:
        return self._raw.values()

    def __contains__(self, key: Union[str, bytes]) -> bool:
        return key in self._parsed if isinstance(key, str) else key in self._raw

    def __getitem__(self, key: Union[str, bytes]) -> Union[bytes, list[str]]:
        return self._parsed[key] if isinstance(key, str) else self._raw[key]


class MutableHeaders(MultiValueDict):
    def __init__(self, initial: dict[str, Union[str, list[str]]] = None):
        super().__init__(initial)

    def encode(self) -> list[tuple[bytes, bytes]]:
        return [
            (k.lower().encode("latin-1"), ", ".join(v).encode("latin-1"))
            for k, v in self.data.items()
        ]
