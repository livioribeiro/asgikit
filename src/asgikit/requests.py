import asyncio
import re
from collections.abc import AsyncIterable
from http import HTTPMethod
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs, unquote_plus

from python_multipart import multipart

from asgikit._json import JSON_DECODER
from asgikit.asgi import AsgiReceive, AsgiScope, AsgiSend
from asgikit.constants import (
    ATTRIBUTES,
    BODY,
    CHARSET,
    CONTENT_LENGTH,
    CONTENT_TYPE,
    COOKIES,
    HEADERS,
    IS_CONSUMED,
    QUERY,
    REQUEST,
    SCOPE_ASGIKIT,
)
from asgikit.errors.http import ClientDisconnectError, RequestBodyAlreadyConsumedError
from asgikit.headers import Headers
from asgikit.query import Query
from asgikit.responses import Response
from asgikit.websockets import WebSocket

__all__ = (
    "Body",
    "Request",
    "read_body",
    "read_text",
    "read_json",
    "read_form",
)

FORM_URLENCODED_CONTENT_TYPE = "application/x-www-urlencoded"
FORM_MULTIPART_CONTENT_TYPE = "multipart/form-data"
FORM_CONTENT_TYPES = (FORM_URLENCODED_CONTENT_TYPE, FORM_MULTIPART_CONTENT_TYPE)

RE_CHARSET = re.compile(r"""charset=([\w-]+|"[\w-]+")""")


def _parse_cookie(data: str) -> dict[str, str]:
    cookie = SimpleCookie()
    cookie.load(data)
    return {key: value.value for key, value in cookie.items()}


class Body:
    """Provides an async iterator over request body"""

    __slots__ = ("_scope", "_receive")

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, headers: Headers):
        self._scope = scope
        self._receive = receive

        if CONTENT_TYPE not in scope[SCOPE_ASGIKIT][REQUEST]:
            content_type = headers.get("content-type")
            self._scope[SCOPE_ASGIKIT][REQUEST][CONTENT_TYPE] = content_type
            if content_type:
                values = RE_CHARSET.findall(self.content_type)
                charset = values[0] if values else "utf-8"
            else:
                charset = "utf-8"
            self._scope[SCOPE_ASGIKIT][REQUEST][CHARSET] = charset

        if CONTENT_LENGTH not in scope[SCOPE_ASGIKIT][REQUEST]:
            if content_length := headers.get("content-length"):
                content_length = int(content_length)
            else:
                content_length = None
            self._scope[SCOPE_ASGIKIT][REQUEST][CONTENT_LENGTH] = content_length

    @property
    def content_type(self) -> str | None:
        return self._scope[SCOPE_ASGIKIT][REQUEST].get(CONTENT_TYPE)

    @property
    def content_length(self) -> int | None:
        return self._scope[SCOPE_ASGIKIT][REQUEST].get(CONTENT_LENGTH)

    @property
    def charset(self) -> str | None:
        return self._scope[SCOPE_ASGIKIT][REQUEST].get(CHARSET)

    @property
    def is_consumed(self) -> bool:
        """Verifies whether the request body is consumed or not"""
        return self._scope[SCOPE_ASGIKIT][REQUEST][IS_CONSUMED]

    def __set_consumed(self):
        self._scope[SCOPE_ASGIKIT][REQUEST][IS_CONSUMED] = True

    async def __aiter__(self) -> AsyncIterable[bytes]:
        """iterate over the bytes of the request body

        :raise RequestBodyAlreadyConsumedError: If the request body is already consumed
        :raise ClientDisconnectError: If the client is disconnected while reading the request body
        """

        if self.is_consumed:
            raise RequestBodyAlreadyConsumedError()

        self.__set_consumed()

        while True:
            message = await self._receive()

            if message["type"] == "http.request":
                yield message["body"]
                if not message["more_body"]:
                    break

            if message["type"] == "http.disconnect":
                raise ClientDisconnectError()


class Request:
    """Represents the incoming request"""

    __slots__ = (
        "scope",
        "asgi_receive",
        "asgi_send",
        "response",
        "websocket",
    )

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        assert scope["type"] in ("http", "websocket")

        if SCOPE_ASGIKIT not in scope:
            scope[SCOPE_ASGIKIT] = {}

        if REQUEST not in scope[SCOPE_ASGIKIT]:
            scope[SCOPE_ASGIKIT][REQUEST] = {}

        if ATTRIBUTES not in scope[SCOPE_ASGIKIT][REQUEST]:
            scope[SCOPE_ASGIKIT][REQUEST][ATTRIBUTES] = {}

        if IS_CONSUMED not in scope[SCOPE_ASGIKIT][REQUEST]:
            scope[SCOPE_ASGIKIT][REQUEST][IS_CONSUMED] = False

        self.scope = scope
        self.asgi_receive = receive
        self.asgi_send = send

        self.response = (
            Response(self.scope, self.asgi_receive, self.asgi_send)
            if self.is_http
            else None
        )
        self.websocket = (
            WebSocket(self.scope, self.asgi_receive, self.asgi_send)
            if self.is_websocket
            else None
        )

    @property
    def attributes(self) -> dict[str, Any]:
        """Request attributes in the scope of asgikit"""
        return self.scope[SCOPE_ASGIKIT][REQUEST][ATTRIBUTES]

    @property
    def is_http(self) -> bool:
        """Tell if the request is an HTTP request

        Returns False for websocket requests
        """
        return self.scope["type"] == "http"

    @property
    def is_websocket(self) -> bool:
        """Tell if the request is a WebSocket request

        Returns False for HTTP requests
        """
        return self.scope["type"] == "websocket"

    @property
    def http_version(self) -> str:
        return self.scope["http_version"]

    @property
    def server(self) -> tuple[str, int | None]:
        return self.scope["server"]

    @property
    def client(self) -> tuple[str, int] | None:
        return self.scope["client"]

    @property
    def scheme(self) -> str:
        return self.scope["scheme"]

    @property
    def method(self) -> HTTPMethod | None:
        """Return None when request is websocket"""

        if method := self.scope.get("method"):
            # pylint: disable=no-value-for-parameter
            return HTTPMethod(method)

        return None

    @property
    def root_path(self) -> str:
        return self.scope["root_path"]

    @property
    def path(self) -> str:
        return self.scope["path"]

    @property
    def raw_path(self) -> str | None:
        return self.scope["raw_path"]

    @property
    def headers(self) -> Headers:
        if HEADERS not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            self.scope[SCOPE_ASGIKIT][REQUEST][HEADERS] = Headers(self.scope["headers"])
        return self.scope[SCOPE_ASGIKIT][REQUEST][HEADERS]

    @property
    def raw_query(self) -> str:
        return unquote_plus(self.scope["query_string"].decode("ascii"))

    @property
    def query(self) -> Query:
        if QUERY not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            self.scope[SCOPE_ASGIKIT][REQUEST][QUERY] = Query(
                self.scope["query_string"]
            )
        return self.scope[SCOPE_ASGIKIT][REQUEST][QUERY]

    @property
    def cookie(self) -> dict[str, str]:
        if COOKIES not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            if cookie := self.headers.get_raw(b"cookie"):
                self.scope[SCOPE_ASGIKIT][REQUEST][COOKIES] = _parse_cookie(
                    cookie.decode("latin-1")
                )
            else:
                self.scope[SCOPE_ASGIKIT][REQUEST][COOKIES] = {}
        return self.scope[SCOPE_ASGIKIT][REQUEST][COOKIES]

    @property
    def body(self) -> Body:
        if BODY not in self.scope[SCOPE_ASGIKIT][REQUEST]:
            self.scope[SCOPE_ASGIKIT][REQUEST][BODY] = Body(
                self.scope, self.asgi_receive, self.headers
            )
        return self.scope[SCOPE_ASGIKIT][REQUEST][BODY]

    @property
    def accept(self) -> str:
        return self.headers["accept"]

    def __getattr__(self, name: str) -> Any:
        if attr := self.scope.get(name):
            return attr

        raise AttributeError(name)

    def __getitem__(self, item):
        return self.attributes[item]

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def __delitem__(self, key):
        del self.attributes[key]

    def __contains__(self, item):
        return item in self.attributes


async def read_body(obj: Body | Request) -> bytes:
    """Read the full request body"""

    body = obj.body if isinstance(obj, Request) else obj
    data = bytearray()

    async for chunk in body:
        data.extend(chunk)

    return bytes(data)


async def read_text(obj: Body | Request, encoding: str = None) -> str:
    """Read the full request body as str"""

    body = obj.body if isinstance(obj, Request) else obj
    data = await read_body(body)
    return data.decode(encoding or body.charset)


async def read_json(obj: Body | Request) -> dict | list:
    """Read the full request body and parse it as json"""

    if data := await read_body(obj):
        return JSON_DECODER(data)
    return {}


def _is_form_multipart(content_type: str) -> bool:
    return content_type.startswith(FORM_MULTIPART_CONTENT_TYPE)


async def read_form(obj: Body | Request) -> dict[str, str | multipart.File]:
    """Read the full request body and parse it as form encoded"""

    body = obj.body if isinstance(obj, Request) else obj

    if _is_form_multipart(body.content_type or ""):
        return await _read_form_multipart(obj)

    data = await read_text(body)
    if not data:
        return {}

    return {
        k: v.pop() if len(v) == 1 else v
        for k, v in parse_qs(data, keep_blank_values=True).items()
    }


async def _read_form_multipart(
    obj: Body | Request,
) -> dict[str, str | multipart.File]:
    fields: dict[str, str] = {}
    files: dict[str, multipart.File] = {}

    body = obj.body if isinstance(obj, Request) else obj
    content_type = body.content_type or ""
    charset = body.charset

    def on_field(field: multipart.Field):
        fields[field.field_name.decode(charset)] = field.value.decode(charset)

    def on_file(file: multipart.File):
        file.file_object.seek(0)
        files[file.field_name.decode(charset)] = file

    headers = {"Content-Type": content_type}
    parser = multipart.create_form_parser(headers, on_field, on_file)

    async for data in body:
        # `parser.write` can potentially write to a file,
        # therefore we need to call it using `asyncio.to_thread`
        await asyncio.to_thread(parser.write, data)

    return fields | files
