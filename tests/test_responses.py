import asyncio
from http import HTTPStatus

from asgikit.requests import Request
from asgikit.responses import (
    Response,
    respond_file,
    respond_json,
    respond_redirect,
    respond_redirect_post_get,
    respond_status,
    respond_stream,
    respond_text,
    stream_writer,
)
from tests.utils.asgi import HttpSendInspector


async def test_respond_plain_text():
    inspector = HttpSendInspector()
    scope = {"type": "http"}
    response = Response(scope, None, inspector)

    await respond_text(response, "Hello, World!")

    assert inspector.body == "Hello, World!"


async def test_respond_json():
    inspector = HttpSendInspector()
    scope = {"type": "http"}
    response = Response(scope, None, inspector)
    await respond_json(response, {"message": "Hello, World!"})

    assert inspector.body == """{"message": "Hello, World!"}"""


async def test_stream():
    async def stream_data():
        yield "Hello, "
        yield "World!"

    inspector = HttpSendInspector()
    scope = {"type": "http", "http_version": "1.1"}
    response = Response(scope, None, inspector)
    await respond_stream(response, stream_data())

    assert inspector.body == "Hello, World!"


async def test_stream_context_manager():
    inspector = HttpSendInspector()
    scope = {"type": "http", "http_version": "1.1"}
    response = Response(scope, None, inspector)

    await response.start()
    async with stream_writer(response) as write:
        await write("Hello, ")
        await write("World!")

    assert inspector.body == "Hello, World!"


async def test_respond_file(tmp_path):
    tmp_file = tmp_path / "tmp_file.txt"
    tmp_file.write_text("Hello, World!")

    inspector = HttpSendInspector()
    scope = {"type": "http", "http_version": "1.1"}

    async def sleep_receive():
        while True:
            await asyncio.sleep(1000)

    response = Response(scope, sleep_receive, inspector)
    await respond_file(response, tmp_file)

    assert inspector.body == "Hello, World!"


async def test_respond_status():
    inspector = HttpSendInspector()
    scope = {"type": "http"}
    response = Response(scope, None, inspector)
    await respond_status(response, HTTPStatus.IM_A_TEAPOT)

    assert inspector.status == HTTPStatus.IM_A_TEAPOT


async def test_respond_empty():
    inspector = HttpSendInspector()
    scope = {"type": "http"}
    response = Response(scope, None, inspector)

    await response.start()
    await response.end()

    assert inspector.status == HTTPStatus.OK
    assert inspector.body == ""


async def test_respond_temporary_redirect():
    inspector = HttpSendInspector()
    scope = {"type": "http"}
    response = Response(scope, None, inspector)
    await respond_redirect(response, "/redirect")

    assert inspector.status == HTTPStatus.TEMPORARY_REDIRECT
    assert inspector.headers["location"] == "/redirect"


async def test_respond_permanent_redirect():
    inspector = HttpSendInspector()
    scope = {"type": "http"}
    response = Response(scope, None, inspector)
    await respond_redirect(response, "/redirect", permanent=True)

    assert inspector.status == HTTPStatus.PERMANENT_REDIRECT
    assert inspector.headers["location"] == "/redirect"


async def test_respond_post_get_redirect():
    inspector = HttpSendInspector()
    scope = {"type": "http"}
    response = Response(scope, None, inspector)
    await respond_redirect_post_get(response, "/redirect")

    assert inspector.status == HTTPStatus.SEE_OTHER
    assert inspector.headers["location"] == "/redirect"
