from pathlib import Path

from asgikit.errors.websocket import WebSocketDisconnectError
from asgikit.requests import HttpRequest
from asgikit.responses import HttpResponse, HTTPStatus, respond_status, respond_file
from asgikit.websockets import WebSocket

clients = set()


async def app(scope, receive, send):
    if scope["type"] == "http":
        request = HttpRequest(scope, receive, send)
        response = HttpResponse(scope, receive, send)

        if request.path == "/favicon.ico":
            await respond_status(response, HTTPStatus.NOT_FOUND)
            return

        await respond_file(response, Path(__file__).parent / "index.html")
        return

    websocket = WebSocket(scope, receive, send)
    await websocket.accept()
    print(f"[open] Client connected")

    clients.add(websocket)

    while True:
        try:
            message = await websocket.receive()
            print(f"[message] {message}")
            for client in clients:
                await client.send_text(message)
        except WebSocketDisconnectError:
            clients.remove(websocket)
            print("[close] Client disconnected")
            break
