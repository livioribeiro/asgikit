from collections import defaultdict
from collections.abc import AsyncIterable, Awaitable, Callable

from asgiref.typing import HTTPRequestEvent, ASGISendEvent

from asgikit.headers import Headers


async def asgi_receive_from_stream(stream: AsyncIterable[bytes]) -> Callable[..., Awaitable]:
    data = [chunk async for chunk in stream]
    data.reverse()

    async def receive() -> HTTPRequestEvent:
        chunk = data.pop()
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": len(data) > 0
        }

    return receive


class AsgiSendInspector:
    def __init__(self):
        self.events: dict[str, list[ASGISendEvent]] = defaultdict(list)

    async def __call__(self, event: ASGISendEvent):
        self.events[event["type"]].append(event)

    @property
    def status(self) -> int:
        return self.events["http.response.start"][0]["status"]

    @property
    def headers(self) -> Headers:
        return Headers(self.events["http.response.start"][0]["headers"])

    @property
    def body(self) -> str:
        result = ""
        for e in self.events["http.response.body"]:
            result += e["body"].decode()

        return result
