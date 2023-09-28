from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple

from asgikit.headers import Headers
from asgikit.query import Query

__all__ = ("HttpConnection", "AsgiContext")


class AsgiContext(NamedTuple):
    scope: dict[str, Any]
    receive: Callable[[], Awaitable[dict[str, Any]]]
    send: Callable[[dict[str, Any]], Awaitable]


class HttpConnection:
    __slots__ = ("_context", "_headers", "_query")

    def __init__(self, scope, receive, send):
        self._context = AsgiContext(scope, receive, send)
        self._headers: Headers | None = None
        self._query: Query | None = None

    @property
    def is_http(self) -> bool:
        return self._context.scope["type"] == "http"

    @property
    def is_websocket(self) -> bool:
        return self._context.scope["type"] == "websocket"

    @property
    def server(self):
        return self._context.scope["server"]

    @property
    def client(self):
        return self._context.scope["client"]

    @property
    def scheme(self):
        return self._context.scope["scheme"]

    @property
    def root_path(self):
        return self._context.scope["root_path"]

    @property
    def path(self):
        return self._context.scope["path"]

    @property
    def raw_path(self):
        return self._context.scope["raw_path"]

    @property
    def headers(self) -> Headers:
        if not self._headers:
            self._headers = Headers(self._context.scope["headers"])
        return self._headers

    @property
    def query(self) -> Query:
        if not self._query:
            self._query = Query(self._context.scope["query_string"])
        return self._query
