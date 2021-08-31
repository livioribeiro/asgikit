# Asgikit - ASGI Toolkit

Toolkit for creating asgi applications

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