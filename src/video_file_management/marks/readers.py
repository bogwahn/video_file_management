from __future__ import annotations

from pathlib import Path

from .chapters_file import ChaptersFile


class ChaptersFileReader:
    """Reads a chapters file into a ChaptersFile instance.

    Expected line format: "[{time:HH:MM:SS.mmm}] Label"
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
            if raw.startswith("[{time:") and "]" in raw:
                # Extract between "[{time:" and "]"
                try:
                    prefix, label = raw.split("]", 1)
                    timecode = prefix[len("[{time:"):]
                    label = label.strip()
                    chapters.add(timecode, label)
                except ValueError:
                    continue
        return chapters 