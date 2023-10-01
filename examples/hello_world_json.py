from asgikit.requests import Request
from asgikit.responses import Response, respond_json


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = Response(scope, receive, send)
    name = request.query.get("name", "World")

    await respond_json(response, {"greeting": "Hello", "name": name, "result": f"Hello, {name}!"})
