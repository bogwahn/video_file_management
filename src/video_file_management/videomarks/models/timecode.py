from __future__ import annotations

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

        hours, remainder = divmod(int(time_delta.total_seconds()), 3600)
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
        try:
            hours_text, minutes_text, seconds_text = value.split(":")
            seconds_part, milliseconds_text = seconds_text.split(".")
            hours = int(hours_text)
            minutes = int(minutes_text)
            seconds = int(seconds_part)
            milliseconds = int(milliseconds_text)
        except ValueError as exc:
            raise ValueError(f"Invalid timecode: {value!r}") from exc

        if (
            hours < 0
            or not 0 <= minutes < 60
            or not 0 <= seconds < 60
            or not 0 <= milliseconds < 1000
            or len(milliseconds_text) != 3
        ):
            raise ValueError(f"Invalid timecode: {value!r}")

        return cls(timedelta(hours=hours, minutes=minutes, seconds=seconds, milliseconds=milliseconds))
