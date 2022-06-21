import asyncio
from pathlib import Path
from tempfile import SpooledTemporaryFile

__all__ = ("UploadedFile",)

BUFFER_SIZE = 8192


def _copy(source: SpooledTemporaryFile, dest: Path):
    with dest.open("wb") as fd, source as src:
        while data := src.read(BUFFER_SIZE):
            fd.write(data)


class UploadedFile:
    __slots__ = ("filename", "content_type", "temporary_file")

    def __init__(
        self, filename: str, content_type: str, temporary_file: SpooledTemporaryFile
    ):
        self.filename = filename
        self.content_type = content_type
        self.temporary_file = temporary_file

    async def save(self, target: str | Path):
        if isinstance(target, str):
            target = Path(target)
        if target.is_dir():
            target = target / self.filename

        await asyncio.to_thread(_copy, self.temporary_file, target)
        del self.temporary_file
