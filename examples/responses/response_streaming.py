from asgikit.requests import HttpRequest
from asgikit.responses import HttpResponse

from . import fibonacci


async def fibonacci_stream(limit: int):
    for i in fibonacci(limit):
        yield f"{i}\n"


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    response = HttpResponse(scope, receive, send)

    limit = int(request.query.get("limit", "10"))

    response.content_type = "text/plain"
    async with response.stream_writer() as write:
        async for data in fibonacci_stream(limit):
            await write(data)
