"""Read existing chapters embedded in a video file."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Protocol

from ...io.readers.metadata import read_file_metadata
from ...marks.formats import ChaptersFile, VideoMarksFile
from ...utils.timecode import format_timecode


class VideoReaderLike(Protocol):
    def read(self, file_path: str) -> VideoMarksFile: ...


class CLIVideoReaderStrategy:
    """Read existing chapters embedded in a video file."""

    def read(self, file_path: str) -> VideoMarksFile:
        chapters_file = ChaptersFile(file_path=file_path)
        meta = read_file_metadata(Path(file_path))
        for chapter in meta.chapters:
            tc_str = format_timecode(timedelta(seconds=chapter.start_seconds))
            chapters_file.add(tc_str, chapter.title)
        return chapters_file
