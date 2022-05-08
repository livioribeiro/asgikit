import json
from enum import Enum
from typing import Any, Dict, List

from asgikit.errors.websocket import (
    WebSocketDisconnectError,
    WebSocketError,
    WebSocketStateError,
)
from asgikit.headers import MutableHeaders
from asgikit.http_connection import HttpConnection


class WebSocket(HttpConnection):
    class State(Enum):
        NEW = 1
        ACCEPTED = 2
        CLOSED = 3

    def __init__(self, scope, receive, send):
        assert scope["type"] == "websocket"
        super().__init__(scope, receive, send)
        self.subprotocols = scope["subprotocols"]
        self._state = self.State.NEW

    async def accept(
        self,
        subprotocol: str = None,
        headers: Dict[str, str | List[str]] | MutableHeaders = None,
    ):
        if self._state != self.State.NEW:
            raise WebSocketStateError()

        message = await self.asgi.receive()
        if message["type"] != "websocket.connect":
            raise WebSocketError()

        if not isinstance(headers, MutableHeaders):
            if headers is None:
                headers = MutableHeaders()
            elif isinstance(headers, (dict, list)):
                headers = MutableHeaders(headers)
            else:
                return ValueError("headers")

        await self.asgi.send(
            {
                "type": "websocket.accept",
                "subprotocol": subprotocol,
                "headers": headers.encode(),
            }
        )

        self._state = self.State.ACCEPTED

    async def receive(self) -> str | bytes:
        if self._state != self.State.ACCEPTED:
            raise WebSocketStateError()

        message = await self.asgi.receive()
        if message["type"] == "websocket.disconnect":
            self._state = self.State.CLOSED
            raise WebSocketDisconnectError(message["code"])

        return message.get("text") or message.get("bytes")

    async def send_text(self, data: str):
        if self._state != self.State.ACCEPTED:
            raise WebSocketStateError()

        await self.asgi.send(
            {
                "type": "websocket.send",
                "text": data,
            }
        )

    async def send_bytes(self, data: bytes):
        if self._state != self.State.ACCEPTED:
            raise WebSocketStateError()

        await self.asgi.send(
            {
                "type": "websocket.send",
                "bytes": data,
            }
        )

    async def send_json(self, data: Dict[str, Any]):
        await self.send_text(json.dumps(data))

    async def close(self, code: int = None):
        if self._state != self.State.ACCEPTED:
            raise WebSocketStateError()

        message = {"type": "websocket.close"}
        if code:
            message["code"] = code

        await self.asgi.send(message)
        self._state = self.State.CLOSED
