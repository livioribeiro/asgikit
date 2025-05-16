from pytest import fixture

from asgikit.files import AsyncFile


@fixture
def tmp_file(tmp_path):
    file = tmp_path / "test_file"
    file.write_text("test")
    return file


async def test_read_file_path(tmp_file):
    file = AsyncFile(tmp_file)

    stat = await file.stat()
    assert stat.st_size == 4

    data = b""
    async with file.stream() as stream:
        async for chunk in stream:
            data += chunk

    assert data == b"test"


async def test_read_file_str_path(tmp_file):
    file = AsyncFile(str(tmp_file))

    stat = await file.stat()
    assert stat.st_size == 4

    data = b""
    async with file.stream() as stream:
        async for chunk in stream:
            data += chunk

    assert data == b"test"


async def test_read_file_chunks(tmp_file, monkeypatch):
    monkeypatch.setenv("ASGIKIT_ASYNC_FILE_CHUNK_SIZE", "1")

    import importlib

    from asgikit import files

    importlib.reload(files)

    from asgikit.files import AsyncFile

    file = AsyncFile(str(tmp_file))

    data = []
    async with file.stream() as stream:
        async for chunk in stream:
            data.append(chunk)

    assert data == [b"t", b"e", b"s", b"t"]
