from pathlib import Path

from asgikit.errors.websocket import WebSocketDisconnectError
from asgikit.request import Request
from asgikit.response import HTTPStatus, respond_file, respond_status
from asgikit.websocket import WebSocket

clients: set[WebSocket] = set()


async def app(scope, receive, send):
    if scope["type"] not in ("http", "websocket"):
        return

    request = Request(scope, receive, send)

    if request.is_http:
        response = request.response

        if request.path == "/favicon.ico":
            await respond_status(response, HTTPStatus.NOT_FOUND)
            return

        await respond_file(response, Path(__file__).parent / "index.html")
        return

    websocket = request.websocket
    await websocket.accept()
    print(f"[open] Client connected")

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
