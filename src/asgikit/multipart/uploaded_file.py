import asyncio
import os
from pathlib import Path

__all__ = ("UploadedFile",)


class UploadedFile:
    __slots__ = ("filename", "content_type", "temporary_path")

    def __init__(self, filename: str, content_type: str, temporary_path: str):
        self.filename = filename
        self.content_type = content_type
        self.temporary_path = Path(temporary_path)

    async def move_file(self, target: str | Path):
        if isinstance(target, str):
            target = Path(target)
        if target.is_dir():
            target = target / self.filename

        await asyncio.to_thread(os.rename, self.temporary_path, target)

    def __del__(self):
        if self.temporary_path.exists():
            os.remove(self.temporary_path)
