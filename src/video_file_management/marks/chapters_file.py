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

    def add(self, timecode: str, label: str) -> None:
        mark = VideoMark(timecode=timecode, label=label)
        if mark not in self._marks:
            self._marks.append(mark)

    def remove(self, identifier: str | int) -> None:
        if isinstance(identifier, int):
            if 0 <= identifier < len(self._marks):
                del self._marks[identifier]
            return
        # Otherwise treat as timecode string
        self._marks = [m for m in self._marks if m.timecode != identifier]

    def marks(self) -> Iterable[VideoMark]:
        return tuple(self._marks)

    def to_string(self) -> str:
        return "\n".join(f"{m.label}: {m.timecode}" for m in self._marks) 