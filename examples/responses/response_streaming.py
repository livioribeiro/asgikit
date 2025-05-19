from asgikit.requests import Request

from . import fibonacci


async def fibonacci_stream(limit: int):
    for i in fibonacci(limit):
        yield f"{i}\n"


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    limit = int(request.query.get("limit", "10"))
    request.response.media_type = "text/plain"

    await request.respond(fibonacci_stream(limit))

    ## alternative with stream_writer
    # async with request.response_writer() as write:
    #     async for data in fibonacci_stream(limit):
    #         await write(data)

    ## alternative with response.write
    # response = request.response
    # async for data in fibonacci_stream(limit):
    #     await response.write(data, more_body=True)
    # await response.end()
