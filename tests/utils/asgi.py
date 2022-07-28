from collections.abc import AsyncIterable, Awaitable, Callable

from asgiref.typing import HTTPRequestEvent


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
