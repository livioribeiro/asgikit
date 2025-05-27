import http.cookies

from ._constants import HEADER_ENCODING


def parse_cookie(cookie: str) -> dict[str, str | list[str]]:
    """
    Return a dictionary parsed from a `Cookie:` header string.
    """
    cookiedict = {}
    for chunk in cookie.split(";"):
        if "=" in chunk:
            key, val = chunk.split("=", 1)
        else:
            # Assume an empty name per
            # https://bugzilla.mozilla.org/show_bug.cgi?id=169091
            key, val = "", chunk
        key, val = key.strip(), val.strip()
        if key or val:
            # unquote using Python's algorithm.
            # pylint: disable=protected-access
            cookiedict[key] = http.cookies._unquote(val)
    return cookiedict


def encode_cookies(cookies: http.cookies.SimpleCookie) -> list[tuple[bytes, bytes]]:
    return [
        (b"Set-Cookie", c.output(header="").strip().encode(HEADER_ENCODING))
        for c in cookies.values()
    ]
