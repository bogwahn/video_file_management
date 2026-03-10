from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..utils.timecode import format_timecode
from .protocols import VideoMarksFile


def generate_nero_chapters_text(chapters: VideoMarksFile) -> str:
    """Generate Nero/MP4Box chapter text format from marks.

    Format:
        CHAPTER01=HH:MM:SS.mmm
        CHAPTER01NAME=Title
    """
    lines: list[str] = []
    for idx, mark in enumerate(chapters.marks(), start=1):
        num = f"{idx:02d}"
        lines.append(f"CHAPTER{num}={format_timecode(mark.timecode)}")
        lines.append(f"CHAPTER{num}NAME={mark.label}")
    return "\n".join(lines) + ("\n" if lines else "")


class ChapterTrackWriter:
    """Creates chapter tracks in MP4 using MP4Box (Nero format).

    This approach creates chapters that start at exact timestamps
    without auto-extension, matching how mChapters app works.
    """

    def write(self, video_file_path: str, chapters: VideoMarksFile) -> None:
        """Write chapters to video file using MP4Box."""
        mp4box = shutil.which("MP4Box")
        if not mp4box:
            return  # MP4Box not available

        video_path = Path(video_file_path)
        if not video_path.exists() or not video_path.is_file():
            return

        # Generate Nero format chapters
        chapters_text = generate_nero_chapters_text(chapters)
        if not chapters_text.strip():
            return  # No chapters to add

        # Create chapters using MP4Box
        try:
            self._embed_chapters_mp4box(str(video_path), chapters_text)
        except Exception:
            return

    def _embed_chapters_mp4box(self, video_path: str, chapters_text: str) -> None:
        """Embed chapters using MP4Box and Nero format."""
        video = Path(video_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            chapters_file = temp_path / "chapters.txt"
            temp_video = temp_path / "temp_with_chapters.mp4"

            # Write Nero chapters file
            chapters_file.write_text(chapters_text, encoding="utf-8")

            # Use MP4Box to add chapters to video
            cmd = [
                "MP4Box",
                "-add",
                str(video),
                "-chap",
                str(chapters_file),
                "-new",
                str(temp_video),
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            # Verify the output file exists and is valid
            if not temp_video.exists() or temp_video.stat().st_size == 0:
                raise RuntimeError("MP4Box chapter embedding failed")

            # Safe atomic replacement
            backup_path = video.with_suffix(video.suffix + ".bak")
            try:
                if backup_path.exists():
                    backup_path.unlink()
                video.rename(backup_path)
                temp_video.rename(video)
                backup_path.unlink()
            except Exception:
                if backup_path.exists() and not video.exists():
                    backup_path.rename(video)
                raise
