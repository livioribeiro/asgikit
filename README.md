# Asgikit - ASGI Toolkit

Asgikit is a toolkit for building asgi applications and frameworks.

It is intended to be a minimal library and provide the building blocks for other libraries.

The [examples directory](./examples) contain usage examples of several use cases

## Features:

- Request
  - Headers
  - Cookies
  - Body (bytes, str, json, form, stream)
  - Form
- Response
  - Plain text
  - Json
  - Streaming
  - File
- Websockets

## Requests and Responses

Asgikit `Request`, like other libraries, have methods to read items from the incoming
request. However, unlike other libraries, there is no response object. Instead, you
use the methods in `Request` to respond to the request like `respond_json` and `respond_stream`.
There is a `response` property in the `Request` object where you can set response
attributes like status, headers and cookies.

The main methods to interact with the `Request` are the following:

```python
class Request:
    # Read the request body as a byte stream
    async def stream(self) -> AsyncIterable[bytes]: ...
    # Read the request body as bytes
    async def read_bytes(self) -> bytes: ...
    # Read the request body as str
    async def read_str(self, encoding: str = None) -> str: ...
    # Read the request body and parse it as json
    async def read_json(self) -> Any: ...
    # Read the request body and parse it as form
    async def read_form(self) -> dict[str, str | list[str]]: ...

    # Respond with bytes
    async def respond_bytes(
        self,
        content: bytes,
        status=HTTPStatus.OK,
        media_type: str = None,
        headers: dict[str, str | list[str]] = None,
    ): ...
    # Respond with str
    async def respond_text(
        self,
        content: str,
        status=HTTPStatus.OK,
        media_type: str = "text/plain",
        headers: dict[str, str | list[str]] = None,
    ): ...
    # Respond with the given content encoded as json
    async def respond_json(
        self,
        content: Any,
        status=HTTPStatus.OK,
        media_type: str = "application/json",
        headers: dict[str, str | list[str]] = None,
    ): ...
    # Respond with empty response and given status
    async def respond_status(
        self, status: HTTPStatus, headers: dict[str, str | list[str]] = None
    ): ...
    # Respond with redirect
    async def redirect(
        self,
        location: str,
        permanent: bool = False,
        headers: dict[str, str | list[str]] = None,
    ): ...
    # Respond with a post/redirect/get
    # https://en.wikipedia.org/wiki/Post/Redirect/Get
    async def redirect_post_get(
        self, location: str, headers: dict[str, str | list[str]] = None
    ): ...
    # Context manager that provides a function to write to the response
    async def response_writer(
        self,
        status=HTTPStatus.OK,
        media_type: str = None,
        headers: dict[str, str | list[str]] = None,
    ): ...
    # Respond with file
    async def respond_file(
        self,
        path: str | os.PathLike,
        status=HTTPStatus.OK,
        media_type: str = None,
        stat_result: os.stat_result = None,
    ): ...
```

## Example request and response

```python
from asgikit.requests import Request


async def main(scope, receive, send):
    assert scope["type"] == "http"

    request = Request(scope, receive, send)

    # request method
    method = request.method

    # request path
    path = request.path

    # request headers
    headers = request.headers

    # read body as json
    body_json = await request.read_json()

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
```

## Example websocket

```python
from asgikit.requests import Request
from asgikit.errors.websocket import WebSocketDisconnectError


async def app(scope, receive, send):
    assert scope["type"] == "websocket"

    request = Request(scope, receive, send)
    ws = request.websocket
    await ws.accept()

    while True:
        try:
            message = await ws.receive()
            await ws.send(message)
        except WebSocketDisconnectError:
            print("Client disconnect")
            break
```
