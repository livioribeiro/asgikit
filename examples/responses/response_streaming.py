from asgikit.requests import Request
from asgikit.responses import Response, stream_writer

from . import fibonacci


async def fibonacci_stream(limit: int):
    for i in fibonacci(limit):
        yield f"{i}\n"


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = Response(scope, receive, send)

    limit = int(request.query.get("limit", "10"))

    response.content_type = "text/plain"
    async with stream_writer(response) as write:
        async for data in fibonacci_stream(limit):
            await write(data)
