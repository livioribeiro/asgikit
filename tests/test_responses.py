import asyncio
import importlib
import sys
from http import HTTPStatus

import pytest

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


@pytest.mark.parametrize(
    "name, encoder",
    [
        ("json", None),
        ("orjson", "orjson"),
        ("orjson", "orjson.loads,orjson.dumps")
    ],
    ids=["json", "orjson", "orjson-direct"],
)
async def test_respond_json(name, encoder, monkeypatch):
    if encoder:
        monkeypatch.setenv("ASGIKIT_JSON_ENCODER", encoder)

    importlib.reload(sys.modules["asgikit._json"])
    from asgikit._json import JSON_ENCODER

    assert JSON_ENCODER.__module__.startswith(name)

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    response = Response(scope, None, inspector)
    await respond_json(response, {"message": "Hello, World!"})

    assert inspector.body == """{"message": "Hello, World!"}"""


@pytest.mark.parametrize("encoder", ["invalid", "module.invalid"])
def test_json_invalid_decoder_should_fail(encoder, monkeypatch):
    monkeypatch.setenv("ASGIKIT_JSON_ENCODER", encoder)
    with pytest.raises(ValueError, match=r"Invalid ASGIKIT_JSON_ENCODER"):
        importlib.reload(sys.modules["asgikit._json"])


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
