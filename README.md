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
    HttpRequest,
    read_body,
    read_text,
    read_json,
    read_form,
)

from asgikit.responses import (
    HttpResponse,
    respond_text,
    respond_json,
    respond_stream,
    respond_file,
    respond_status,
    respond_redirect,
    respond_redirect_post_get,
)

async def main(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    response = HttpResponse(scope, receive, send)

    # request headers
    headers = request.headers

    body_stream = bytearray()
    # read body as stream
    async for chunk in request.stream():
        body_stream += chunk
  
    # read body as bytes
    body_bytes = await read_body(request)

    # read body as text
    body_text = await read_text(request)
  
    # read body as json
    body_json = await read_json(request)

    # read body as form
    body_form = await read_form(request)

    # send json response
    data = {"lang": "Python", "async": True, "platform": "asgi"}
    await respond_json(response, data)
```

## Example websocket

```python
from asgikit.websockets import WebSocket
from asgikit.errors.websocket import WebSocketDisconnectError

async def app(scope, receive, send):
    websocket = WebSocket(scope, receive, send)
    await websocket.accept()

    while True:
        try:
            message = await websocket.receive()
            await websocket.send_text(message)
        except WebSocketDisconnectError:
            print("Client disconnect")
            break
```
