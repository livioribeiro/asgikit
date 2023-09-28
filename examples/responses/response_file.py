from pathlib import Path

from asgikit.responses import HttpResponse, respond_file


async def app(scope, receive, send):
    response = HttpResponse(scope, receive, send)
    file = Path(__file__).parent / "python-powered.png"
    await respond_file(response, file)
