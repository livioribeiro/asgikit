from pathlib import Path

from asgikit.requests import HttpRequest
from asgikit.responses import FileResponse


async def app(scope, receive, send):
    request = HttpRequest(scope, receive, send)
    file = Path(__file__).parent / "python-powered.png"
    response = FileResponse(file)
    await response(request)
