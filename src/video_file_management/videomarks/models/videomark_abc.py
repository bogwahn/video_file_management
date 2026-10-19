from __future__ import annotations

from abc import ABC, abstractmethod

from .timecode import TimeCode


class VideoMarkABC(ABC):
    """Base class for video marks."""

    def __init__(self, time: TimeCode, label: str) -> None:
        self.time = time
        self.label = label

    @abstractmethod
    def to_string(self) -> str:
        """Serialize this mark using its file-format representation."""
