from typing import Awaitable, Callable, NamedTuple

from .headers import Headers
from .query import Query

__all__ = ("HttpConnection",)


class HttpConnection:
    __slots__ = ("_asgi_scope", "_asgi_receive", "_asgi_send", "_headers", "_query")

    def __init__(self, scope: dict, receive: Callable[..., Awaitable], send: Callable[..., Awaitable]):
        self._asgi_scope = scope
        self._asgi_receive = receive
        self._asgi_send = send

        self._headers: Headers | None = None
        self._query: Query | None = None

    @property
    def is_http(self) -> bool:
        return self._asgi_scope["type"] == "http"

    @property
    def is_websocket(self) -> bool:
        return self._asgi_scope["type"] == "websocket"

    @property
    def server(self):
        return self._asgi_scope["server"]

    @property
    def client(self):
        return self._asgi_scope["client"]

    @property
    def scheme(self):
        return self._asgi_scope["scheme"]

    @property
    def root_path(self):
        return self._asgi_scope["root_path"]

    @property
    def path(self):
        return self._asgi_scope["path"]

    @property
    def raw_path(self):
        return self._asgi_scope["raw_path"]

    @property
    def headers(self) -> Headers:
        if not self._headers:
            self._headers = Headers(self._asgi_scope["headers"])
        return self._headers

    @property
    def query(self) -> Query:
        if not self._query:
            self._query = Query(self._asgi_scope["query_string"])
        return self._query
