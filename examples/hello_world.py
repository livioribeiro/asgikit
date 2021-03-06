from asgikit.requests import HttpRequest
from asgikit.responses import PlainTextResponse


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    name = request.query.get("name", "World")

    response = PlainTextResponse(f"Hello, {name}!")
    await response(request)
