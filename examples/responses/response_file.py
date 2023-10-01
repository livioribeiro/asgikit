from pathlib import Path

from asgikit.responses import Response, respond_file


async def app(scope, receive, send):
    response = Response(scope, receive, send)
    file = Path(__file__).parent / "python-powered.png"
    await respond_file(response, file)
