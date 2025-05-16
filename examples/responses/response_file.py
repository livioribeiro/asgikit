from pathlib import Path

from asgikit.requests import Request


async def app(scope, receive, send):
    request = Request(scope, receive, send)
    file = Path(__file__).parent / "python-powered.png"
    await request.respond(file)
