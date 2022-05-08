import asyncio
import os
from pathlib import Path


class UploadedFile:
    def __init__(self, filename: str, content_type: str, temporary_path: str):
        self.filename = filename
        self.content_type = content_type
        self.temporary_path = Path(temporary_path)

    async def move_file(self, target: str | Path):
        if isinstance(target, str):
            target = Path(target)
        if target.is_dir():
            target = target / self.filename

        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, os.rename, self.temporary_path, target)

    def __del__(self):
        if self.temporary_path.exists():
            os.remove(self.temporary_path)
