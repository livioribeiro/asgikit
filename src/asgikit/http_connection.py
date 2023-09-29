from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple

from asgikit.headers import Headers
from asgikit.query import Query

__all__ = ("HttpConnection", "AsgiContext")


_ATTRIBUTES_KEY = "attributes"


class AsgiContext(NamedTuple):
    scope: dict[str, Any]
    receive: Callable[[], Awaitable[dict[str, Any]]]
    send: Callable[[dict[str, Any]], Awaitable]


class HttpConnection:
    __slots__ = ("_context", "_headers", "_query")

    def __init__(self, scope, receive, send):
        if _ATTRIBUTES_KEY not in scope:
            scope[_ATTRIBUTES_KEY]: dict[str, Any] = {}

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

    @property
    def attibutes(self) -> dict[str, Any]:
        return self._context.scope[_ATTRIBUTES_KEY]

    def __getitem__(self, item):
        return self._context.scope[_ATTRIBUTES_KEY][item]

    def __setitem__(self, key, value):
        self._context.scope[_ATTRIBUTES_KEY][key] = value

    def __delitem__(self, key):
        del self._context.scope[_ATTRIBUTES_KEY][key]

    def __contains__(self, item):
        return item in self._context.scope[_ATTRIBUTES_KEY]
