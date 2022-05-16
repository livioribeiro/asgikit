from pathlib import Path

from asgikit.responses import FileResponse


async def app(scope, receive, send):
    file = Path(__file__).parent / "python-powered.png"
    response = FileResponse(file)
    await response(scope, receive, send)
