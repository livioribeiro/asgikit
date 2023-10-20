from enum import Enum

from asgikit.asgi import AsgiProtocol, AsgiReceive, AsgiScope, AsgiSend
from asgikit.errors.websocket import (
    WebSocketDisconnectError,
    WebSocketError,
    WebSocketStateError,
)
from asgikit.headers import MutableHeaders

__all__ = ("WebSocket",)


class WebSocket:
    class State(Enum):
        NEW = 1
        ACCEPTED = 2
        CLOSED = 3

    __slots__ = ("_asgi", "_state")

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        self._asgi = AsgiProtocol(scope, receive, send)
        self._state = self.State.NEW

    @property
    def subprotocols(self) -> list[str]:
        return self._asgi.scope["subprotocols"]

    @property
    def state(self) -> State:
        return self._state

    async def accept(
        self,
        subprotocol: str = None,
        headers: dict[str, str | list[str]] | MutableHeaders = None,
    ):
        if self._state != self.State.NEW:
            raise WebSocketStateError()

        message = await self._asgi.receive()
        if message["type"] != "websocket.connect":
            # TODO: improve error message
            raise WebSocketError()

        if not isinstance(headers, MutableHeaders):
            if headers is None:
                headers = MutableHeaders()
            elif isinstance(headers, (dict, list)):
                headers = MutableHeaders(headers)
            else:
                return ValueError("headers")

        await self._asgi.send(
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

        message = await self._asgi.receive()
        if message["type"] == "websocket.disconnect":
            self._state = self.State.CLOSED
            raise WebSocketDisconnectError(message["code"])

        return message.get("text") or message.get("bytes")

    async def send(self, data: bytes | str):
        if self._state != self.State.ACCEPTED:
            raise WebSocketStateError()

        if isinstance(data, bytes):
            data_field = "bytes"
        elif isinstance(data, str):
            data_field = "text"
        else:
            raise TypeError("must be 'bytes' or 'str'")

        await self._asgi.send(
            {
                "type": "websocket.send",
                data_field: data,
            }
        )

    async def close(self, code: int = 1000, reason: str = ""):
        if self._state != self.State.ACCEPTED:
            raise WebSocketStateError()

        await self._asgi.send(
            {
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            }
        )

        self._state = self.State.CLOSED
