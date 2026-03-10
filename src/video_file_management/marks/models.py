from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class VideoMark:
    """Represents a single mark within a media timeline.

    Attributes:
        timecode: Offset from start, as datetime.timedelta.
        label: A short descriptive label for the mark.
    """

    timecode: timedelta
    label: str
