from asgikit.requests import HttpRequest
from asgikit.responses import StreamingResponse

from . import fibonacci


async def fibonacci_stream(limit: int):
    yield '{"fibonacci": {'

    n = limit - 1
    for i, fib in enumerate(fibonacci(limit)):
        yield f'"{i}": {fib}{", " if i < n else ""}'

    yield "} }"


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    limit = int(request.query.get("limit", "10"))

    response = StreamingResponse(fibonacci_stream(limit), content_type="application/json")
    await response(request)
