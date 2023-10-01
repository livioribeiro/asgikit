# Asgikit - ASGI Toolkit

Asgikit is a toolkit for building asgi applications and frameworks.

It is intended to be a minimal library and provide the building blocks for other libraries.

The [examples directory](./examples) contain usage examples of several use cases

## Features:

- Request
  - Headers
  - Cookies
  - Body (bytes, str, json, stream)
  - Form
- Response
  - Plain text
  - Json
  - Streaming
  - File
- Websockets

## Request and Response

Asgikit `HttpRequest` and `HttpResponse` were designed to be have minimal interfaces,
so they only provide very few methods to read from the request and write to the response.
In particular, the `HttpResponse` works differently from most tools, in which you do not
return a response, but you write data into it.

It is provided several functions to interact with the request and the response, for instance,
to read form data from the request and write json to the response.

This strategy allows for simpler extensibility. For example, to parse json from the request
using an alternative json parser, you just need to write a function that reads the request.
Similarly, to write another data format into the response, you just write a function that
writes to the response.

## Example request and response

```python
from asgikit.requests import (
  Request,
  read_json,
)

from asgikit.responses import (
  Response,
  respond_json,
)


async def main(scope, receive, send):
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
```

## Example websocket

```python
from asgikit.requests import Request
from asgikit.errors.websocket import WebSocketDisconnectError

async def app(scope, receive, send):
    request = Request(scope, receive, send)
    ws = request.websocket()
    await ws.accept()

    while True:
        try:
            message = await ws.receive()
            await ws.send(message)
        except WebSocketDisconnectError:
            print("Client disconnect")
            break
```
