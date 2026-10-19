from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Resolution:
    """Frame size of a video stream in pixels."""

    width: int
    height: int

    def to_string(self) -> str:
        return f"{self.width}x{self.height}"
