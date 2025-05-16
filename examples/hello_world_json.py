from asgikit.requests import Request


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    name = request.query.get("name", "World")

    data = {"greeting": "Hello", "name": name, "result": f"Hello, {name}!"}
    await request.respond(data)
