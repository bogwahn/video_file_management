from __future__ import annotations

from abc import ABC
from collections.abc import Iterable

from .videomark import VideoMark
from .videomarks_file import VideoMarksFile


class VideoMarksFileABC(VideoMarksFile, ABC):
    """ABC for video marks files."""

    def __init__(self, videomarks: Iterable[VideoMark] = ()) -> None:
        self._marks: list[VideoMark] = list(videomarks)

    def addMark(self, videomark: VideoMark) -> None:
        self._marks.append(videomark)

    def removeMark(self, videomark: VideoMark) -> None:
        self._marks.remove(videomark)

    def videomarks(self) -> Iterable[VideoMark]:
        return tuple(self._marks)

    def to_string(self) -> str:
        return "\n".join(videomark.to_string() for videomark in self._marks)
