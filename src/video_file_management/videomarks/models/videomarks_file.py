from __future__ import annotations

from typing import Iterable, Protocol

from .videomark import VideoMark


class VideoMarksFile(Protocol):
    """Protocol for video marks files."""

    def addMark(self, video_mark: VideoMark) -> None: ...
    def removeMark(self, video_mark: VideoMark) -> None: ...
    def videomarks(self) -> Iterable[VideoMark]: ...
    def to_string(self) -> str: ...
