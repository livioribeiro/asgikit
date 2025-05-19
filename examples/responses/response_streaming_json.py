from collections.abc import AsyncIterable

from asgikit.requests import Request

from . import fibonacci


async def fibonacci_stream(limit: int) -> AsyncIterable[bytes]:
    yield b'{"fibonacci": ['

    n = limit - 1
    for i, fib in enumerate(fibonacci(limit)):
        yield f"{fib}{', ' if i < n else ''}".encode()

    yield b"] }"


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    limit = int(request.query.get("limit", "10"))

    request.response.media_type = "application/json"

    await request.respond(fibonacci_stream(limit))
