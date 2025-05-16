from asyncio.locks import Event
from collections import defaultdict
from collections.abc import AsyncIterable, Awaitable, Callable

from asgiref.typing import ASGIReceiveEvent, ASGISendEvent, HTTPRequestEvent


async def asgi_receive_from_stream(
    stream: AsyncIterable[bytes],
) -> Callable[..., Awaitable]:
    data = [chunk async for chunk in stream]
    data.reverse()

    async def receive() -> HTTPRequestEvent:
        chunk = data.pop()
        return {"type": "http.request", "body": chunk, "more_body": len(data) > 0}

    return receive


class AsgiReceiveInspector:
    def __init__(self):
        self._sync = Event()
        self.events: list[ASGIReceiveEvent] = []

    def send(self, event: ASGIReceiveEvent):
        self.events.append(event)
        self._sync.set()

    async def __call__(self) -> ASGIReceiveEvent:
        if not self.events:
            await self._sync.wait()
            self._sync.clear()

        return self.events.pop()


class WebSocketSendInspector:
    def __init__(self):
        self.events: dict[str, list[ASGISendEvent]] = defaultdict(list)
        self.subprotocol: str | None = None
        self.headers: dict[str, list[str]] | None = None
        self.bytes: list[bytes] = []
        self.text: list[str] = []
        self.close_code: int | None = None
        self.close_reason: str | None = None

    async def __call__(self, event: ASGISendEvent):
        match event["type"]:
            case "websocket.accept":
                self.subprotocol = event["subprotocol"]
                self.headers = dict(event["headers"]) if event["headers"] else {}
            case "websocket.send":
                if "bytes" in event and (data := event["bytes"]):
                    self.bytes.append(data)
                if "text" in event and (data := event["text"]):
                    self.text.append(data)
            case "websocket.close":
                self.close_code = event["code"]
                self.close_reason = event["reason"]

        self.events[event["type"]].append(event)


class HttpSendInspector:
    def __init__(self):
        self.events: dict[str, list[ASGISendEvent]] = defaultdict(list)
        self.status: int | None = None
        self.headers: list[tuple[bytes, bytes]] | None = None
        self._body = bytearray()

    async def __call__(self, event: ASGISendEvent):
        match event["type"]:
            case "http.response.start":
                self.status = event["status"]
                self.headers = event["headers"]
            case "http.response.body":
                self._body.extend(event["body"])

        self.events[event["type"]].append(event)

    @property
    def body(self) -> str:
        return self._body.decode()
