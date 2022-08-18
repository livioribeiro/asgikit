import asyncio
from http import HTTPStatus

from asgikit.requests import HttpRequest
from asgikit.responses import HttpResponse
from tests.utils.asgi import HttpSendInspector


async def test_plain_text():
    response = HttpResponse.text("Hello, World!")

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.body == "Hello, World!"


async def test_json():
    response = HttpResponse.json({"message": "Hello, World!"})

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.body == """{"message": "Hello, World!"}"""


async def test_stream():
    async def stream_data():
        yield "Hello, "
        yield "World!"

    response = HttpResponse.stream(stream_data())

    inspector = HttpSendInspector()
    scope = {"type": "http", "http_version": "1.1"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.body == "Hello, World!"


async def test_file(tmp_path):
    tmp_file = tmp_path / "tmp_file.txt"
    tmp_file.write_text("Hello, World!")

    response = HttpResponse.file(tmp_file)

    inspector = HttpSendInspector()
    scope = {"type": "http", "http_version": "1.1"}

    async def sleep_receive():
        while True:
            await asyncio.sleep(1000)

    request = HttpRequest(scope, sleep_receive, inspector)
    await response(request)

    assert inspector.body == "Hello, World!"


async def test_response_ok():
    response = HttpResponse.ok("Hello, World!")

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.OK
    assert inspector.body == "Hello, World!"


async def test_response_ok_empty():
    response = HttpResponse.ok()

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.OK
    assert inspector.body == ""


async def test_response_not_found():
    response = HttpResponse.not_found("not found")

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.NOT_FOUND
    assert inspector.body == "not found"


async def test_response_not_found_empty():
    response = HttpResponse.not_found()

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.NOT_FOUND
    assert inspector.body == ""


async def test_response_accepted():
    response = HttpResponse.accepted()

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.ACCEPTED


async def test_response_no_content():
    response = HttpResponse.no_content()

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.NO_CONTENT


async def test_response_temporary_redirect():
    response = HttpResponse.redirect("/redirect")

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.TEMPORARY_REDIRECT
    assert inspector.headers["location"] == "/redirect"


async def test_response_permanent_redirect():
    response = HttpResponse.redirect("/redirect", permanent=True)

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.PERMANENT_REDIRECT
    assert inspector.headers["location"] == "/redirect"


async def test_response_post_get_redirect():
    response = HttpResponse.redirect_post_get("/redirect")

    inspector = HttpSendInspector()
    scope = {"type": "http"}
    request = HttpRequest(scope, None, inspector)
    await response(request)

    assert inspector.status == HTTPStatus.SEE_OTHER
    assert inspector.headers["location"] == "/redirect"
