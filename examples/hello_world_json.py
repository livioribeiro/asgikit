from asgikit.requests import HttpRequest
from asgikit.responses import HttpResponse, respond_json


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    response = HttpResponse(scope, receive, send)
    name = request.query.get("name", "World")

    await respond_json(response, {"greeting": "Hello", "name": name, "result": f"Hello, {name}!"})
