"""Result models for chapterize operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class ProcessingStatus(Enum):
    """Status of a chapterize processing operation."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class ChapterizeResult:
    """Result of a chapterize operation on a single video file.

    Attributes:
        video_path: Path to the video file that was processed.
        status: Processing status (success, failed, or skipped).
        chapters_path: Path to the chapters file used, if found.
        message: Human-readable message describing the result.
        error: Exception or error details if processing failed.
    """

    video_path: Path
    status: ProcessingStatus
    chapters_path: Optional[Path] = None
    message: str = ""
    error: Optional[Exception] = None

    @property
    def succeeded(self) -> bool:
        """True if processing succeeded."""
        return self.status == ProcessingStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """True if processing failed."""
        return self.status == ProcessingStatus.FAILED

    @property
    def skipped(self) -> bool:
        """True if processing was skipped."""
        return self.status == ProcessingStatus.SKIPPED
