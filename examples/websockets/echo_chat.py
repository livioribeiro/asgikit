from http import HTTPStatus
from pathlib import Path

from asgikit.errors.websocket import WebSocketDisconnectError
from asgikit.requests import Request
from asgikit.websockets import WebSocket

clients: set[WebSocket] = set()


async def app(scope, receive, send):
    if scope["type"] not in ("http", "websocket"):
        return

    request = Request(scope, receive, send)

    if request.is_http:
        if request.path == "/favicon.ico":
            await request.respond(HTTPStatus.NOT_FOUND)
            return

        await request.respond(Path(__file__).parent / "index.html")
        return

    websocket = request.websocket
    await websocket.accept()
    print("[open] Client connected")

    clients.add(websocket)

    while True:
        try:
            message = await websocket.receive()
            print(f"[message] {message}")
            for client in clients:
                await client.send(message)
        except WebSocketDisconnectError:
            clients.remove(websocket)
            print("[close] Client disconnected")
            break
