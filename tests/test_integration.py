from httpx import ASGITransport, AsyncClient

from asgikit.requests import Request


async def test_request_response():
    async def app(scope, receive, send):
        request = Request(scope, receive, send)
        await request.respond("Ok")

    client = AsyncClient(transport=ASGITransport(app))
    response = await client.get("http://localhost:8000/")
    assert response.text == "Ok"
