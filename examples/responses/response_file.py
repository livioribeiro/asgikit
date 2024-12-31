from pathlib import Path

from asgikit.request import Request
from asgikit.response import respond_file


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    response = request.response
    file = Path(__file__).parent / "python-powered.png"
    await respond_file(response, file)
