from __future__ import annotations

from pathlib import Path

from .chapters_file import ChaptersFile


class BookmarksFileReader:
    """Reads simple bookmark files into a ChaptersFile instance.

    Expected line format per bookmark:
        HH:MM:SS.mmm,Label
    The hour component may omit leading zeros (e.g. "0:10:05.647").
    Empty lines and comment lines starting with "//" are ignored.
    """

    def read(self, file_path: str) -> ChaptersFile:
        chapters = ChaptersFile(file_path=file_path)
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return chapters

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
                chapters.add(time_text, label_text)
            except ValueError:
                # Skip malformed timecodes; validation handled by ChaptersFile.
                continue
        return chapters
