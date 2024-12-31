from asgikit.request import Request
from asgikit.response import respond_json


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = request.response
    name = request.query.get("name", "World")

    await respond_json(
        response, {"greeting": "Hello", "name": name, "result": f"Hello, {name}!"}
    )
