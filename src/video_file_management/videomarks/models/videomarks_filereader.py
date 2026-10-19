from __future__ import annotations

from typing import Protocol

from .videomarks_file import VideoMarksFile


class VideoMarksFileReader(Protocol):
    """Reader for video marks files."""

    def read(self) -> VideoMarksFile: ...
