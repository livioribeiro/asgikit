# Asgikit - ASGI Toolkit

Asgikit is a toolkit for building asgi applications and frameworks.

It is intended to be a minimal library and provide the building blocks for other libraries.

## Features:

- Request
  - Headers
  - Cookies
  - Body (bytes, str, json)
  - Form
    - url encoded
    - multipart
- Response
  - Plain text
  - Json
  - Streaming
  - File
- Websockets

## Example

```python
from asgikit.requests import HttpRequest
from asgikit.responses import JsonResponse

async def main(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    body = await request.json()
    data = {"lang": "Python", "async": True}
    response = JsonResponse(content=data)
    await response(scope, receive, send)
```