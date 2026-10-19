"""Result record for a single chapterize input."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class ProcessResult:
    source_input: Path
    status: str
    message: str
    video_path: Optional[Path] = None
    marks_path: Optional[Path] = None
    elapsed_seconds: float = 0.0
    index: int = 0
