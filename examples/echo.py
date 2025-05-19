from http import HTTPMethod, HTTPStatus

from asgikit.requests import Request


async def app(scope, receive, send):
    request = Request(scope, receive, send)

    # request method
    method = request.method

    if method != HTTPMethod.POST:
        await request.respond_status(HTTPStatus.METHOD_NOT_ALLOWED)
        return

    # request path
    path = request.path

    # request headers
    headers = request.headers

    # read body as json
    body_json = await request.body.json()

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
    await request.respond_json(data)
