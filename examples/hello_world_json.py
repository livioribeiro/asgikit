from asgikit.requests import HttpRequest
from asgikit.responses import JsonResponse


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    name = request.query.get_first("name", "World")

    response = JsonResponse({"greeting": "Hello", "name": name, "result": f"Hello, {name}!"})
    await response(scope, receive, send)