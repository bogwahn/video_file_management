from __future__ import annotations

import re
from datetime import timedelta


class TimeCode:
    __slots__ = ("_hours", "_minutes", "_seconds", "_milliseconds")

    def __init__(self, time_delta: timedelta | None = None) -> None:
        if time_delta is None:
            self._hours = 0
            self._minutes = 0
            self._seconds = 0
            self._milliseconds = 0
            return

        if time_delta < timedelta(0):
            raise ValueError("Timecode cannot be negative")

        total_seconds = time_delta.days * 86400 + time_delta.seconds
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self._hours = hours
        self._minutes = minutes
        self._seconds = seconds
        self._milliseconds = time_delta.microseconds // 1000

    @property
    def hours(self) -> int:
        return self._hours

    @property
    def minutes(self) -> int:
        return self._minutes

    @property
    def seconds(self) -> int:
        return self._seconds

    @property
    def milliseconds(self) -> int:
        return self._milliseconds

    def to_string(self) -> str:
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}.{self.milliseconds:03d}"

    @classmethod
    def from_string(cls, value: str) -> TimeCode:
        """Create a timecode from an HH:MM:SS.mmm string."""
        match = re.fullmatch(r"([0-9]{2,}):([0-5][0-9]):([0-5][0-9])\.([0-9]{3})", value)
        if match is None:
            raise ValueError(f"Invalid timecode: {value!r}")

        hours, minutes, seconds, milliseconds = (int(field) for field in match.groups())
        return cls(timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds))
