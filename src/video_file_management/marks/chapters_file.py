from __future__ import annotations

from typing import Iterable, List

from .models import VideoMark
from .protocols import VideoMarksFile


class ChaptersFile(VideoMarksFile):
    """Concrete marks container for chapters.

    Serializes as "Label: HH:MM:SS" lines.
    """

    def __init__(self) -> None:
        self._marks: List[VideoMark] = []

    def add_mark(self, mark: VideoMark) -> None:
        if mark not in self._marks:
            self._marks.append(mark)

    def add(self, mark: VideoMark) -> None:
        self.add_mark(mark)

    def remove_mark(self, mark: VideoMark) -> None:
        try:
            self._marks.remove(mark)
        except ValueError:
            pass

    def remove(self, mark: VideoMark) -> None:
        self.remove_mark(mark)

    def marks(self) -> Iterable[VideoMark]:
        return tuple(self._marks)

    def to_string(self) -> str:
        return "\n".join(f"{m.label}: {m.timecode}" for m in self._marks) 