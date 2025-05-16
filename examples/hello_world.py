from asgikit.requests import Request


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    name = request.query.get("name", "World")

    greeting = f"Hello, {name}!"

    request.response.content_type = "text/plain"
    request.response.content_length = len(greeting)
    await request.respond(greeting)
