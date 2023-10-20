from asgikit.requests import Request
from asgikit.responses import respond_text


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = request.response
    name = request.query.get("name", "World")

    greeting = f"Hello, {name}!"

    response.content_type = "text/plain"
    response.content_length = len(greeting)
    await response.start()
    await response.write(greeting, end_response=True)

    # # shortcut
    # await respond_text(response, greeting)
