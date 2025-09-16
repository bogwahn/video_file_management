from __future__ import annotations

from typing import Iterable, Protocol

from .models import VideoMark


class VideoMarksFile(Protocol):
    """Protocol for a collection of VideoMark entries.

    Implementations decide how marks are formatted when serialized.
    Implementations should parse the provided timecode string into a
    datetime.timedelta for internal storage.
    """

    file_path: str

    def add(self, timecode: str, label: str) -> None:
        ...

    def remove(self, identifier: str | int) -> None:
        """Remove by timecode (str) or position (int)."""
        ...

    def marks(self) -> Iterable[VideoMark]:
        ...

    def to_string(self) -> str:
        ... 