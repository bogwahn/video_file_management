"""Atomic video writer strategy for the Chapterize Video feature."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from video_file_management.chapterize.controller import VideoWriterStrategy
from video_file_management.chapterize.interfaces import UserPromptStrategy
from video_file_management.marks.models import VideoMark


def _generate_mp4box_chapters(marks: Iterable[VideoMark]) -> str:
    """Generates the OGG text format expected by MP4Box.

    Format: HH:MM:SS.mmm Chapter Title
    Example: 00:00:00.000 Intro
    """
    lines = []
    sorted_marks = sorted(marks, key=lambda m: m.timecode)

    for mark in sorted_marks:
        ms = int(mark.timecode.microseconds / 1000)
        s = mark.timecode.seconds
        h, rem = divmod(s, 3600)
        m, s = divmod(rem, 60)

        tc_str = f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
        lines.append(f"{tc_str} {mark.label}")

    return "\n".join(lines) + "\n"


class MP4ChaptersWriterAtomic(VideoWriterStrategy):
    """Embeds chapters using MP4Box.

    To avoid NAS network I/O corruption (e.g. 'Unknown top-level box type'),
    the file is securely copied to a local temporary workspace, mutated
    by GPAC/MP4Box, and then successfully transferred back, safely replacing the original.
    """

    def __init__(self, prompt: UserPromptStrategy) -> None:
        self.prompt = prompt

    def write(self, video_path: str, marks: Iterable[VideoMark]) -> None:
        """Writes the provided marks to the target video instantly in-place."""
        mp4box = shutil.which("MP4Box")
        if not mp4box:
            self.prompt.notify_error("MP4Box is not installed (run `brew install gpac`).")
            raise RuntimeError("MP4Box missing")

        video_file = Path(video_path)
        if not video_file.exists() or not video_file.is_file():
            self.prompt.notify_error(f"Target video not found: {video_path}")
            raise FileNotFoundError(video_path)

        chapters_content = _generate_mp4box_chapters(marks)
        if not chapters_content.strip():
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            local_video = workspace / video_file.name
            temp_text_file = workspace / f"chapters_{video_file.stem}.txt"

            try:
                # 1. Transfer to local workspace to avoid network I/O corruption
                shutil.copy2(video_file, local_video)
                temp_text_file.write_text(chapters_content, encoding="utf-8")

                # 2. Use MP4Box to inject the text file locally
                cmd = [mp4box, "-chap", str(temp_text_file), str(local_video)]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.prompt.notify_error(f"MP4Box failed to embed chapters: {result.stderr}")
                    raise RuntimeError(f"MP4Box error: {result.stderr}")

                # 3. Transfer the successfully mutated file back to replace the original
                shutil.move(str(local_video), str(video_file))

            except Exception as e:
                # If anything fails natively or during transfer, we do not touch the original NAS file
                if not isinstance(e, RuntimeError):
                    self.prompt.notify_error(f"Failed to cleanly apply chapters: {str(e)}")
                raise
