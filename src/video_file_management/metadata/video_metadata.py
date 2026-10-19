from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .file_metadata import AudioStreamInfo, FileMetadata, VideoStreamInfo


@dataclass(slots=True)
class ChapterMetadata:
    start_seconds: float
    title: str


@dataclass(slots=True)
class VideoFileMetadata(FileMetadata):
    """Metadata for video files: container, streams, chapters, tags."""

    format_name: Optional[str] = None
    runtime_seconds: Optional[float] = None
    video: VideoStreamInfo = field(default_factory=VideoStreamInfo)
    audio: AudioStreamInfo = field(default_factory=AudioStreamInfo)
    chapters: list[ChapterMetadata] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
