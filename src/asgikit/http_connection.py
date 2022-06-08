from typing import Awaitable, Callable, NamedTuple

from .headers import Headers
from .query import Query

__all__ = ("AsgiCallbacks", "HttpConnection")


class AsgiCallbacks(NamedTuple):
    receive: Callable[..., Awaitable]
    send: Callable[..., Awaitable]


class HttpConnection:
    __slots__ = ("scope", "asgi_callbacks", "_headers", "_query")

    def __init__(self, scope, receive, send):
        self.scope = scope
        self.asgi_callbacks = AsgiCallbacks(receive, send)

        self._headers: Headers | None = None
        self._query: Query | None = None

    @property
    def is_http(self) -> bool:
        return self.scope["type"] == "http"

    @property
    def is_websocket(self) -> bool:
        return self.scope["type"] == "websocket"

    @property
    def server(self):
        return self.scope["server"]

    @property
    def client(self):
        return self.scope["client"]

    @property
    def scheme(self):
        return self.scope["scheme"]

    @property
    def root_path(self):
        return self.scope["root_path"]

    @property
    def path(self):
        return self.scope["path"]

    @property
    def raw_path(self):
        return self.scope["raw_path"]

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
