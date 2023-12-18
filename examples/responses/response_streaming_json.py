from collections.abc import AsyncIterable

from asgikit.requests import Request
from asgikit.responses import respond_stream

from . import fibonacci


async def fibonacci_stream(limit: int) -> AsyncIterable[bytes]:
    yield '{"fibonacci": ['

    n = limit - 1
    for i, fib in enumerate(fibonacci(limit)):
        yield f'{fib}{", " if i < n else ""}'

    yield "] }"


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = request.response
    limit = int(request.query.get("limit", "10"))

    response.content_type = "application/json"

    await respond_stream(response, fibonacci_stream(limit))
