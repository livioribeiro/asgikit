from enum import StrEnum

from asgikit.asgi import AsgiReceive, AsgiScope, AsgiSend
from asgikit.errors.websocket import (
    WebSocketDisconnectError,
    WebSocketError,
    WebSocketStateError,
)
from asgikit.headers import MutableHeaders

__all__ = ("WebSocket",)


class WebSocket:
    """Represents a WebSocket connection"""

    class State(StrEnum):
        """State of the WebSocket connection"""

        NEW = "NEW"
        ACCEPTED = "ACCEPTED"
        CLOSED = "CLOSED"

    __slots__ = ("_scope", "_receive", "_send", "__state")

    def __init__(self, scope: AsgiScope, receive: AsgiReceive, send: AsgiSend):
        self._scope = scope
        self._receive = receive
        self._send = send
        self.__state = self.State.NEW

    @property
    def state(self) -> State:
        """Return the current state of the WebSocket connection"""
        return self.__state

    @property
    def subprotocols(self) -> list[str]:
        """Return a list of subprotocols of this WebSocket connection"""
        return self._scope["subprotocols"]

    async def accept(
        self,
        subprotocol: str = None,
        headers: dict[str, str | list[str]] | MutableHeaders = None,
    ):
        """Initialize the WebSocket connection

        Must be called before interacting with the WebSocket connection
        :raise WebSocketStateError: If the WebSocket state is not NEW
        :raise WebSocketError:
        """
        if self.state != self.State.NEW:
            raise WebSocketStateError()

        message = await self._receive()
        if message["type"] != "websocket.connect":
            # TODO: can be improved?
            raise WebSocketError()

        if not isinstance(headers, MutableHeaders):
            if headers is None:
                headers = MutableHeaders()
            elif isinstance(headers, (dict, list)):
                headers = MutableHeaders(headers)
            else:
                return ValueError("headers")

        await self._send(
            {
                "type": "websocket.accept",
                "subprotocol": subprotocol,
                "headers": headers.encode(),
            }
        )

        self.__state = self.State.ACCEPTED

    async def receive(self) -> str | bytes:
        """Receive data from the WebSocket connection

        :raise WebSocketStateError: If the WebSocket state is not ACCEPTED
        :raise WebSocketDisconnectError: if the client disconnect
        """

        if self.state != self.State.ACCEPTED:
            raise WebSocketStateError()

        message = await self._receive()
        if message["type"] == "websocket.disconnect":
            self.__state = self.State.CLOSED
            raise WebSocketDisconnectError(message["code"])

        return message.get("text") or message.get("bytes")

    async def send(self, data: bytes | str):
        """Send data to the WebSocket connection

        :raise WebSocketStateError: If the WebSocket state is not ACCEPTED
        :raise TypeError: If data is not bytes or str
        """

        if self.state != self.State.ACCEPTED:
            raise WebSocketStateError()

        if isinstance(data, bytes):
            data_field = "bytes"
        elif isinstance(data, str):
            data_field = "text"
        else:
            raise TypeError("must be 'bytes' or 'str'")

        await self._send(
            {
                "type": "websocket.send",
                data_field: data,
            }
        )

    async def close(self, code: int = 1000, reason: str = ""):
        """Close the WebSocket connection

        :raise WebSocketStateError: If the WebSocket state is not ACCEPTED
        """

        if self.state != self.State.ACCEPTED:
            raise WebSocketStateError()

        await self._send(
            {
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            }
        )

        self.__state = self.State.CLOSED
