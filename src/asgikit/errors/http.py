from asgikit.errors.asgi import AsgiError


class HttpError(AsgiError):
    pass


class ClientDisconnectError(HttpError):
    pass
