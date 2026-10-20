from __future__ import annotations

from collections.abc import Iterable

from .chapter import Chapter
from .videomark import VideoMark
from .videomarks_file_abc import VideoMarksFileABC


class ChaptersFile(VideoMarksFileABC):
    """Concrete marks container for chapters.

    Serializes as "[HH:MM:SS.mmm] Label" lines.
    """

    def __init__(self, chapters: Iterable[Chapter] = ()) -> None:
        marks = list(chapters)
        if any(not isinstance(mark, Chapter) for mark in marks):
            raise TypeError("ChaptersFile only accepts Chapter marks")
        super().__init__(marks)

    def addMark(self, videomark: VideoMark) -> None:
        if not isinstance(videomark, Chapter):
            raise TypeError("ChaptersFile only accepts Chapter marks")
        super().addMark(videomark)

    @property
    def Chapters(self) -> list[Chapter]:
        return [mark for mark in self._marks if isinstance(mark, Chapter)]
