"""Loading of marks from chapters and bookmarks files."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ...io.readers import BookmarksFileReader, ChaptersFileReader
from ...marks.formats import VideoMarksFile
from ...marks.models import VideoMark


class MarksLoaderLike(Protocol):
    def load(self, path: Path, kind: str) -> list[VideoMark]: ...


class MarksLoader:
    """Load marks from chapters/bookmarks files."""

    def load(self, path: Path, kind: str) -> list[VideoMark]:
        marks_file: VideoMarksFile
        if kind == "bookmarks":
            marks_file = BookmarksFileReader().read(str(path))
        else:
            marks_file = ChaptersFileReader().read(str(path))
        return list(marks_file.marks())
