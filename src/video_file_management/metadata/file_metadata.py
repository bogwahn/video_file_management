from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class VideoStreamInfo:
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    bit_depth: Optional[int] = None


@dataclass(slots=True)
class AudioStreamInfo:
    codec: Optional[str] = None
    channels: Optional[int] = None
    sample_rate: Optional[int] = None


@dataclass(slots=True)
class FileMetadata(ABC):
    """Abstract base for file metadata containers."""

    path: Path
    errors: list[str] = field(default_factory=list)
