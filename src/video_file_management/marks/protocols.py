from __future__ import annotations

from typing import Iterable, Protocol

from .models import VideoMark


class VideoMarksFile(Protocol):
    """Protocol for a collection of VideoMark entries.

    Implementations decide how marks are formatted when serialized.
    """

    def add_mark(self, mark: VideoMark) -> None:
        ...

    def remove_mark(self, mark: VideoMark) -> None:
        ...

    def add(self, mark: VideoMark) -> None:
        ...

    def remove(self, mark: VideoMark) -> None:
        ...

    def marks(self) -> Iterable[VideoMark]:
        ...

    def to_string(self) -> str:
        ... 