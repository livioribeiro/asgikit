from pathlib import Path

from asgikit.errors.websocket import WebSocketDisconnectError
from asgikit.requests import HttpRequest
from asgikit.responses import FileResponse, HttpResponse, HTTPStatus
from asgikit.websockets import WebSocket


async def app(scope, receive, send):
    if scope["type"] == "http":
        request = HttpRequest(scope, receive, send)

        if request.path == "/favicon.ico":
            response = HttpResponse(status=HTTPStatus.NOT_FOUND)
            await response(request)
            return

        response = FileResponse(Path(__file__).parent / "index.html")
        await response(request)
        return

    websocket = WebSocket(scope, receive, send)
    await websocket.accept()
    print(f"[open] Client connected")

    while True:
        try:
            message = await websocket.receive()
            print(f"[message] {message}")
            await websocket.send_text(message)
        except WebSocketDisconnectError:
            print("[close] Client disconnected")
            break
