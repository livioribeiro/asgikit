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
There is a `response` in the `Request` object where you can set response status, headers and cookies.

## Example request and response

```python
from asgikit.requests import Request


async def main(scope, receive, send):
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
