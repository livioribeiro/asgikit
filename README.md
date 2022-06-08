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
    - url encoded
- Response
  - Plain text
  - Json
  - Streaming
  - File
- Websockets

## Example request and response

```python
from asgikit.requests import HttpRequest
from asgikit.responses import JsonResponse

async def main(scope, receive, send):
    request = HttpRequest(scope, receive, send)

    # request headers
    headers = request.headers

    body_stream = bytearray()
    # read body as stream
    async for chunk in request.stream():
      body_stream += chunk
  
    # read body as bytes
    body_bytes = await request.body()

    # read body as text
    body_text = await request.text()
  
    # read body as json
    body_json = await request.json()

    # read body as form
    body_form = await request.form()

    # send json response
    data = {"lang": "Python", "async": True, "web_platform": "asgi"}
    response = JsonResponse(data)
    await response(request)
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
