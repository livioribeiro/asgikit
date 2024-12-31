from asgikit.errors.asgi import AsgiError


class HttpError(AsgiError):
    pass


class ClientDisconnectError(HttpError):
    pass


class RequestBodyAlreadyConsumedError(HttpError):
    pass


class ResponseAlreadyStartedError(HttpError):
    pass


class ResponseNotStartedError(HttpError):
    pass


class ResponseAlreadyEndedError(HttpError):
    pass
