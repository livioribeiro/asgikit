from asgikit.requests import Request

async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        return

    request = Request(scope, receive, send)
    data = await request.read_json()
    print(data)
    await request.respond_text("")