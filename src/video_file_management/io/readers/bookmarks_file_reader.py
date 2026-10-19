from __future__ import annotations

from pathlib import Path

from ...marks.formats import BookmarksFile
from .file_reader import FileReader


class BookmarksFileReader(FileReader[BookmarksFile]):
    """Reads simple bookmark files into a BookmarksFile instance.

    Expected line format per bookmark:
        HH:MM:SS.mmm,Label
    The hour component may omit leading zeros (e.g. "0:10:05.647").
    Empty lines and comment lines starting with "//" are ignored.
    """

    def read(self, file_path: str) -> BookmarksFile:
        bookmarks = BookmarksFile(file_path=file_path)
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return bookmarks

        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            if "," not in line:
                continue
            time_text, label_text = line.split(",", 1)
            time_text = time_text.strip()
            label_text = label_text.strip()
            if not time_text or not label_text:
                continue
            try:
                bookmarks.add(time_text, label_text)
            except ValueError:
                continue
        return bookmarks
