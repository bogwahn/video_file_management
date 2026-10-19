from __future__ import annotations

from typing import Protocol

from .videomarks_file import VideoMarksFile


class VideoMarksFileWriter(Protocol):
    """Writer for video marks files."""

    def write(self, file: VideoMarksFile) -> None: ...
