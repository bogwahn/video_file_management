from __future__ import annotations

from datetime import timedelta


def parse_timecode(value: str) -> timedelta:
    """Parse timecode "HH:MM:SS.mmm" into timedelta.

    Accepts hours >= 0, minutes 0-59, seconds 0-59, milliseconds 0-999.
    """
    try:
        hh_mm, ss_mmm = value.rsplit(":", 1)
        hours_str, minutes_str = hh_mm.split(":", 1)
        seconds_str, millis_str = (ss_mmm.split(".", 1) + ["0"])[:2]
        hours = int(hours_str)
        minutes = int(minutes_str)
        seconds = int(seconds_str)
        millis = int((millis_str + "000")[:3])
        if (
            minutes < 0
            or minutes > 59
            or seconds < 0
            or seconds > 59
            or millis < 0
            or millis > 999
        ):
            raise ValueError
        return timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=millis,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid timecode: {value}") from exc


def format_timecode(delta: timedelta) -> str:
    """Format timedelta as "HH:MM:SS.mmm"."""
    total_ms = int(delta.total_seconds() * 1000)
    hours, rem_ms = divmod(total_ms, 3600 * 1000)
    minutes, rem_ms = divmod(rem_ms, 60 * 1000)
    seconds, millis = divmod(rem_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}" 