from asgikit.requests import (
    HttpRequest,
    read_json,
)

from asgikit.responses import (
    HttpResponse,
    respond_json,
)


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    response = HttpResponse(scope, receive, send)

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
