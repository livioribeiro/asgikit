from typing import Awaitable, Callable, NamedTuple

from .headers import Headers
from .query import Query


class AsgiCallbacks(NamedTuple):
    receive: Callable[..., Awaitable]
    send: Callable[..., Awaitable]


class HttpConnection:
    def __init__(self, scope, receive, send):
        self.scope = scope
        self.asgi = AsgiCallbacks(receive, send)

        self.server = scope["server"]
        self.client = scope["client"]
        self.scheme = scope["scheme"]
        self.root_path = scope["root_path"]
        self.path = scope["path"]
        self.raw_path = scope["raw_path"]

        self._headers = None
        self._query = None

    @property
    def headers(self) -> Headers:
        if not self._headers:
            self._headers = Headers(self.scope["headers"])
        return self._headers

    @property
    def query(self) -> Query:
        if not self._query:
            self._query = Query(self.scope["query_string"])
        return self._query
