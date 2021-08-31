import urllib.parse
from itertools import chain

from .utils import MultiValueDict


class Query(MultiValueDict):
    def __init__(self, query_string: bytes, encoding="utf-8"):
        decoded_qs = query_string.decode(encoding)
        parsed_qs = urllib.parse.parse_qs(decoded_qs, keep_blank_values=True)
        super().__init__(parsed_qs)

    def __str__(self) -> str:
        query = list(
            chain.from_iterable(
                [(key, v) for v in values] for key, values in self.items()
            )
        )
        return urllib.parse.urlencode(query)

    def encode(self, encoding="utf-8") -> bytes:
        return str(self).encode(encoding)
