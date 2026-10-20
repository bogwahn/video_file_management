from __future__ import annotations

from pathlib import Path
from typing import Protocol

from video_file_management.videomarks.models import ChaptersFile

from .ffmpeg_writer import FFmpegChapterWriter
from .mp4box_writer import MP4BoxChapterWriter


class ChapterWriter(Protocol):
    def write(self, video_path: Path, chapters: ChaptersFile) -> None: ...


class ChapterTrackWriter:
    """Route MP4 files to MP4Box and other supported containers to FFmpeg."""

    def __init__(
        self,
        mp4box_writer: ChapterWriter | None = None,
        ffmpeg_writer: ChapterWriter | None = None,
    ) -> None:
        self._mp4box_writer = MP4BoxChapterWriter() if mp4box_writer is None else mp4box_writer
        self._ffmpeg_writer = FFmpegChapterWriter() if ffmpeg_writer is None else ffmpeg_writer

    def write(self, video_path: str | Path, chapters: ChaptersFile) -> None:
        source = Path(video_path)
        writer = self._mp4box_writer if source.suffix.casefold() == ".mp4" else self._ffmpeg_writer
        writer.write(source, chapters)
