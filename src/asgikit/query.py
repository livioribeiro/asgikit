import urllib.parse
from itertools import chain

from asgikit.util.multi_value_dict import MultiStrValueDict

__all__ = ("Query",)


class Query(MultiStrValueDict):
    def __init__(self, query_string: bytes = None):
        if query_string:
            decoded_qs = query_string.decode("ascii")
            parsed_qs = urllib.parse.parse_qs(decoded_qs, keep_blank_values=True)
            super().__init__(parsed_qs)
        else:
            super().__init__()

    def encode(self) -> bytes:
        return str(self).encode("ascii")

    def __str__(self) -> str:
        query = list(
            chain.from_iterable(
                [(key, v) for v in values] for key, values in self.items()
            )
        )
        return urllib.parse.urlencode(query)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Query):
            return self.data == o.data
        if isinstance(o, dict):
            return self.data == o
        if isinstance(o, str):
            return self.data == Query(o.encode("ascii")).data
        if isinstance(o, bytes):
            return self.data == Query(o).data
        return False
