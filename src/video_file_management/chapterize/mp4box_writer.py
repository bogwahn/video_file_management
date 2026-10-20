from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from video_file_management.videomarks.models import ChaptersFile

from .writer_utils import replace_source


class MP4BoxChapterWriter:
    """Write an MP4 chapter track using MP4Box's Nero chapter format."""

    @staticmethod
    def to_nero_text(chapters: ChaptersFile) -> str:
        lines: list[str] = []
        for index, chapter in enumerate(chapters.Chapters, start=1):
            number = f"{index:02d}"
            lines.append(f"CHAPTER{number}={chapter.time.to_string()}")
            lines.append(f"CHAPTER{number}NAME={chapter.label}")
        return "\n".join(lines) + ("\n" if lines else "")

    def write(self, video_path: str | Path, chapters: ChaptersFile) -> None:
        source = Path(video_path)
        if not source.is_file():
            raise FileNotFoundError(source)
        if not chapters.Chapters:
            raise ValueError("Cannot write an empty chapter list")

        mp4box = shutil.which("MP4Box")
        if mp4box is None:
            raise FileNotFoundError("MP4Box executable was not found")

        with tempfile.TemporaryDirectory(prefix=f".{source.stem}.chapterize-", dir=source.parent) as temp_dir:
            temp_directory = Path(temp_dir)
            chapters_file = temp_directory / "chapters.txt"
            output_video = temp_directory / source.name
            chapters_file.write_text(self.to_nero_text(chapters), encoding="utf-8")

            command = [
                mp4box,
                "-add",
                str(source),
                "-chap",
                str(chapters_file),
                "-new",
                str(output_video),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"MP4Box failed to write chapters to {source}") from exc

            replace_source(source, output_video, "MP4Box")
