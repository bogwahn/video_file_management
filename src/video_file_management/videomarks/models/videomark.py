from __future__ import annotations

from typing import Protocol

from .timecode import TimeCode


class VideoMark(Protocol):
    """Protocol for a single mark on a media timeline."""

    time: TimeCode
    label: str

    def to_string(self) -> str: ...
