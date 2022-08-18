from asgikit.websockets import WebSocket
from tests.utils.asgi import AsgiReceiveInspector, WebSocketSendInspector


async def test_websocket():
    scope = {
        "type": "websocket",
        "subprotocols": ["stomp"],
    }

    receive = AsgiReceiveInspector()
    send = WebSocketSendInspector()

    ws = WebSocket(scope, receive, send)

    receive.send(
        {
            "type": "websocket.connect",
        }
    )

    await ws.accept(subprotocol="stomp")

    assert send.subprotocol == "stomp"
