from __future__ import annotations

from pathlib import Path

from .chapters_file import ChaptersFile
from ..utils.timecode import parse_timecode


class ChaptersFileReader:
    """Reads a chapters file into a ChaptersFile instance.

    Expected line format: "[HH:MM:SS.mmm] Label"
    Lines not matching the expected format are ignored.
    """

    def read(self, file_path: str) -> ChaptersFile:
        chapters = ChaptersFile(file_path=file_path)
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return chapters

        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            if raw.startswith("[") and "]" in raw:
                try:
                    close_idx = raw.index("]")
                    timecode_str = raw[1:close_idx]
                    label = raw[close_idx + 1:].strip()
                    if timecode_str and label:
                        # Parse to validate. The add() method will parse again
                        # when constructing the VideoMark instance.
                        parse_timecode(timecode_str)
                        chapters.add(timecode_str, label)
                except ValueError:
                    continue
        return chapters 