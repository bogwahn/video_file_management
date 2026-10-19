"""Merge logic for handling chapter conflicts."""

from __future__ import annotations

from typing import Iterable, Protocol

from ...marks.models import VideoMark


class MergeServiceLike(Protocol):
    def merge(self, existing: Iterable[VideoMark], incoming: Iterable[VideoMark]) -> list[VideoMark]: ...


class MergeService:
    """Merge marks by timecode and keep first occurrence for each timestamp."""

    def merge(self, existing: Iterable[VideoMark], incoming: Iterable[VideoMark]) -> list[VideoMark]:
        ordered = sorted(list(existing) + list(incoming), key=lambda m: m.timecode)
        merged: list[VideoMark] = []
        seen = set()
        for mark in ordered:
            if mark.timecode in seen:
                continue
            seen.add(mark.timecode)
            merged.append(mark)
        return merged
