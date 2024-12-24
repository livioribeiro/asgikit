from asgikit.request import Request
from asgikit.response import respond_stream, stream_writer

from . import fibonacci


async def fibonacci_stream(limit: int):
    for i in fibonacci(limit):
        yield f"{i}\n"


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = request.response

    limit = int(request.query.get("limit", "10"))

    response.content_type = "text/plain"

    await respond_stream(response, fibonacci_stream(limit))

    ## alternative with stream_writer
    # async with stream_writer(response) as write:
    #     async for data in fibonacci_stream(limit):
    #         await write(data)

    ## alternative with response.write
    # async for data in fibonacci_stream(limit):
    #     await response.write(data, more_body=True)
    # await response.end()
