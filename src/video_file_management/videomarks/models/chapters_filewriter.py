from __future__ import annotations

from pathlib import Path

from .videomarks_file import VideoMarksFile
from .videomarks_filewriter import VideoMarksFileWriter


class ChaptersFileWriter(VideoMarksFileWriter):
    """Write chapter marks to a text file."""

    def __init__(self, file_path: str) -> None:
        self._file_path = Path(file_path)

    def write(self, file: VideoMarksFile) -> None:
        self._file_path.write_text(file.to_string(), encoding="utf-8")
