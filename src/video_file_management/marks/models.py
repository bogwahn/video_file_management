from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VideoMark:
    """Represents a single mark within a media timeline.

    Attributes:
        timecode: Human-readable time string (e.g., "00:01:23").
        label: A short descriptive label for the mark.
    """

    timecode: str
    label: str 