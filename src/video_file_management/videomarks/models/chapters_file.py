from __future__ import annotations

from collections.abc import Iterable

from .chapter import Chapter
from .videomarks_file_abc import VideoMarksFileABC


class ChaptersFile(VideoMarksFileABC):
    """Concrete marks container for chapters.

    Serializes as "[HH:MM:SS.mmm] Label" lines.
    """

    def __init__(self, chapters: Iterable[Chapter] = ()) -> None:
        super().__init__(chapters)

    @property
    def Chapters(self) -> list[Chapter]:
        return [mark for mark in self._marks if isinstance(mark, Chapter)]
