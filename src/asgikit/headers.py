from ._constants import HEADER_ENCODING


def parse_headers(raw_headers: list[tuple[bytes, bytes]]) -> dict[str, str | list[str]]:
    result = {}

    for raw_name, raw_value in raw_headers:
        name = raw_name.decode(HEADER_ENCODING)
        value = raw_value.decode(HEADER_ENCODING)

        if name in result:
            if isinstance(result[name], list):
                result[name].append(value)
            else:
                result[name] = [result[name], value]
        else:
            result[name] = value

    return dict(result)


def encode_headers(headers: dict[str, str | list[str]]) -> list[tuple[bytes, bytes]]:
    result = []

    for name, value in headers.items():
        encoded_name = name.encode(HEADER_ENCODING)

        if isinstance(value, str):
            encoded_value = value.encode(HEADER_ENCODING)
        elif isinstance(value, (list, set, tuple)):
            encoded_value = ", ".join(value).encode(HEADER_ENCODING)
        else:
            raise TypeError()

        result.append((encoded_name, encoded_value))

    return result
