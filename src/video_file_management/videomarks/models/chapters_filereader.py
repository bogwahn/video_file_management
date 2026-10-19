from __future__ import annotations

from pathlib import Path

from .chapter import Chapter
from .chapters_file import ChaptersFile
from .timecode import TimeCode
from .videomarks_filereader import VideoMarksFileReader


class ChaptersFileReader(VideoMarksFileReader):
    """Read chapter marks from a bracketed-timecode text file."""

    def __init__(self, file_path: str) -> None:
        self._file_path = Path(file_path)

    def read(self) -> ChaptersFile:
        chapters = ChaptersFile()
        for line_number, raw_line in enumerate(self._file_path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if not line.startswith("[") or "]" not in line:
                raise ValueError(f"Invalid chapter at line {line_number}: expected [timecode] label")

            close_bracket = line.index("]")
            time_text = line[1:close_bracket].strip()
            label = line[close_bracket + 1 :].strip()
            try:
                timecode = TimeCode.from_string(time_text)
            except ValueError as exc:
                raise ValueError(f"Invalid chapter timecode at line {line_number}") from exc

            chapters.addMark(Chapter(timecode, label))

        return chapters
