from asgikit.requests import HttpRequest
from asgikit.responses import StreamingResponse

from . import fibonacci


async def fibonacci_stream(limit: int):
    for i in fibonacci(limit):
        yield f"{i}\n"


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    limit = int(request.query.get_first("limit", "10"))

    response = StreamingResponse(fibonacci_stream(limit), content_type="text/plain")
    await response(scope, receive, send)
