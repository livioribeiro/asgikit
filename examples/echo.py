from asgikit.requests import (
    Request,
    read_json,
)

from asgikit.responses import (
    Response,
    respond_json,
)


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = Response(scope, receive, send)

    # request method
    method = request.method

    # request path
    path = request.path

    # request headers
    headers = request.headers

    # read body as json
    body_json = await read_json(request)

    data = {
        "lang": "Python",
        "async": True,
        "platform": "asgi",
        "method": method,
        "path": path,
        "headers": dict(headers.items()),
        "body": body_json,
    }

    # send json response
    await respond_json(response, data)
