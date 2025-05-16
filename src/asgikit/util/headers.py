import itertools
from collections import defaultdict

HEADER_ENCODING = "latin-1"


def parse_headers(raw_headers: list[tuple[bytes, bytes]]) -> dict[str, list[str]]:
    result = defaultdict(list)
    for name, value in raw_headers:
        result[name.decode()].append(value.decode())
    return dict(result)


def encode_headers(headers: dict[str, list[str]]) -> list[tuple[bytes, bytes]]:
    encoded = [
        [
            (name.encode(HEADER_ENCODING), value.encode(HEADER_ENCODING))
            for value in value_list
        ]
        for name, value_list in headers.items()
    ]

    return list(itertools.chain.from_iterable(encoded))
