from asgikit.requests import Request
from tests.utils.asgi import AsgiReceiveInspector, WebSocketSendInspector


async def test_websocket():
    scope = {
        "type": "websocket",
        "subprotocols": ["stomp"],
    }

    receive = AsgiReceiveInspector()
    send = WebSocketSendInspector()

    request = Request(scope, receive, send)
    ws = request.websocket
    assert ws is not None

    receive.send(
        {
            "type": "websocket.connect",
        }
    )

    await ws.accept(subprotocol="stomp")

    assert send.subprotocol == "stomp"


async def test_non_websocket_request():
    scope = {
        "type": "http",
    }

    request = Request(scope, None, None)
    ws = request.websocket
    assert ws is None
