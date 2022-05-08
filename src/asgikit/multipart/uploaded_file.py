import asyncio
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UploadedFile:
    filename: str
    content_type: str
    temporary_path: str

    async def move_file(self, target: str | Path):
        if isinstance(target, str):
            target = Path(target)
        if target.is_dir():
            target = target / self.filename

        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, os.rename, self.temporary_path, target)

    def __del__(self):
        if Path(self.temporary_path).exists():
            os.remove(self.temporary_path)
