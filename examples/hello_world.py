from asgikit.request import Request
from asgikit.response import respond_text


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = request.response
    name = request.query.get("name", "World")

    greeting = f"Hello, {name}!"

    response.content_type = "text/plain"
    response.content_length = len(greeting)
    await response.start()
    await response.write(greeting)

    ## shortcut
    # await respond_text(response, greeting)
