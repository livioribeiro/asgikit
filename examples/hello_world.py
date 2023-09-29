from asgikit.requests import HttpRequest
from asgikit.responses import HttpResponse, respond_text


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    response = HttpResponse(scope, receive, send)
    name = request.query.get("name", "World")

    greeting = f"Hello, {name}!"

    response.content_type = "text/plain"
    response.content_length = len(greeting)
    await response.start()
    await response.write(greeting, response_end=True)

    # # shortcut
    # await respond_text(response, greeting)
