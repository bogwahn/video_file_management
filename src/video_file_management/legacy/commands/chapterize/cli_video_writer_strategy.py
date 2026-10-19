"""Write chapters into videos using the atomic MP4 writer."""

from __future__ import annotations

from typing import Iterable, Protocol

from ...io.writers import MP4ChaptersWriter
from ...marks.formats import ChaptersFile
from ...marks.models import VideoMark
from ...utils.timecode import format_timecode


class VideoWriterLike(Protocol):
    def write(self, video_path: str, marks: Iterable[VideoMark]) -> None: ...


class CLIVideoWriterStrategy:
    """Write chapters into videos using atomic MP4 writer."""

    def write(self, video_path: str, marks: Iterable[VideoMark]) -> None:
        chapters = ChaptersFile(file_path=video_path)
        for mark in marks:
            chapters.add(format_timecode(mark.timecode), mark.label)
        MP4ChaptersWriter().write(video_path, chapters)
