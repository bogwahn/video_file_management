from __future__ import annotations

from .videomark_abc import VideoMarkABC


class Bookmark(VideoMarkABC):
    """Bookmark mark for bookmark files Bookmark format: HH:MM:SS.mmm,Label"""

    def to_string(self) -> str:
        return f"{self.time.to_string()},{self.label}"
