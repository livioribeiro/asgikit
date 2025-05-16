from asgikit.requests import Request


async def receive_wrapper(receive) -> dict:
    event = await receive()
    print(f"received {event['type']}")
    return event


async def send_wrapper(send, event: dict):
    print(f"sending {event['type']}")
    await send(event)


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    request.wrap_asgi(receive=receive_wrapper, send=send_wrapper)

    name = request.query.get("name", "World")
    greeting = f"Hello, {name}!"

    await request.respond(greeting)
