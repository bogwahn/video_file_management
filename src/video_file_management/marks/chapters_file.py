from __future__ import annotations

from typing import Iterable, List

from .models import VideoMark
from .protocols import VideoMarksFile
from ..utils.timecode import parse_timecode, format_timecode


class ChaptersFile(VideoMarksFile):
    """Concrete marks container for chapters.

    Serializes as "[HH:MM:SS.mmm] Label" lines.
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._marks: List[VideoMark] = []

    def add(self, timecode: str, label: str) -> None:
        mark = VideoMark(timecode=parse_timecode(timecode), label=label)
        if mark not in self._marks:
            self._marks.append(mark)

    def remove(self, identifier: str | int) -> None:
        if isinstance(identifier, int):
            if 0 <= identifier < len(self._marks):
                del self._marks[identifier]
            return
        # Otherwise treat as timecode string
        try:
            target = parse_timecode(identifier)
            self._marks = [m for m in self._marks if m.timecode != target]
        except Exception:
            pass

    def marks(self) -> Iterable[VideoMark]:
        return tuple(self._marks)

    def to_string(self) -> str:
        return "\n".join(
            f"[{format_timecode(m.timecode)}] {m.label}" for m in self._marks
        ) 