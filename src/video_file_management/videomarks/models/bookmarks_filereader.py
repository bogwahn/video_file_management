from __future__ import annotations

from pathlib import Path

from .bookmark import Bookmark
from .bookmarks_file import BookmarksFile
from .timecode import TimeCode
from .videomarks_filereader import VideoMarksFileReader


class BookmarksFileReader(VideoMarksFileReader):
    """Read bookmark marks from a comma-separated text file."""

    def __init__(self, file_path: str) -> None:
        self._file_path = Path(file_path)

    def read(self) -> BookmarksFile:
        bookmarks = BookmarksFile()
        for line_number, raw_line in enumerate(self._file_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if "," not in line:
                raise ValueError(f"Invalid bookmark at line {line_number}: expected timecode,label")

            time_text, label = line.split(",", 1)
            try:
                timecode = TimeCode.from_string(time_text.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid bookmark timecode at line {line_number}") from exc

            bookmarks.addMark(Bookmark(timecode, label.strip()))

        return bookmarks
