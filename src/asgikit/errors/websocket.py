from .asgi import AsgiError


class WebSocketError(AsgiError):
    pass


class WebSocketStateError(WebSocketError):
    pass


class WebSocketDisconnectError(WebSocketError):
    def __init__(self, code: int):
        self.code = code
        super().__init__(f"client disconnected with code: {code}")
