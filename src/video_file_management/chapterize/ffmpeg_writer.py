from __future__ import annotations

import shutil
import subprocess
import tempfile
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from video_file_management.videomarks.models import Chapter, ChaptersFile

from .writer_utils import replace_source


class FFmpegChapterWriter:
    """Remux non-MP4 containers with native chapter metadata, without re-encoding."""

    @staticmethod
    def to_ffmetadata(chapters: ChaptersFile, *, duration_ms: int) -> str:
        chapter_marks = sorted(chapters.Chapters, key=FFmpegChapterWriter._to_milliseconds)
        if not chapter_marks:
            raise ValueError("Cannot write an empty chapter list")

        starts = [FFmpegChapterWriter._to_milliseconds(chapter) for chapter in chapter_marks]
        if starts[0] < 0 or starts[-1] >= duration_ms:
            raise ValueError("Chapter timestamps must fall within the video duration")
        if any(start >= end for start, end in zip(starts, [*starts[1:], duration_ms], strict=True)):
            raise ValueError("Chapter timestamps must be distinct and increasing")

        lines = [";FFMETADATA1", ""]
        for index, chapter in enumerate(chapter_marks):
            end = starts[index + 1] if index + 1 < len(starts) else duration_ms
            lines.extend(
                [
                    "[CHAPTER]",
                    "TIMEBASE=1/1000",
                    f"START={starts[index]}",
                    f"END={end}",
                    f"title={FFmpegChapterWriter._escape_metadata(chapter.label)}",
                    "",
                ]
            )
        return "\n".join(lines)

    def write(self, video_path: str | Path, chapters: ChaptersFile) -> None:
        source = Path(video_path)
        if not source.is_file():
            raise FileNotFoundError(source)
        if not chapters.Chapters:
            raise ValueError("Cannot write an empty chapter list")

        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if ffmpeg is None or ffprobe is None:
            missing = "ffmpeg" if ffmpeg is None else "ffprobe"
            raise FileNotFoundError(f"{missing} executable was not found")

        duration_ms = self._read_duration_ms(ffprobe, source)
        with tempfile.TemporaryDirectory(prefix=f".{source.stem}.chapterize-", dir=source.parent) as temp_dir:
            temp_directory = Path(temp_dir)
            metadata_file = temp_directory / "chapters.ffmeta"
            output_video = temp_directory / source.name
            metadata_file.write_text(
                self.to_ffmetadata(chapters, duration_ms=duration_ms),
                encoding="utf-8",
            )

            command = [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-f",
                "ffmetadata",
                "-i",
                str(metadata_file),
                "-map",
                "0",
                "-map_metadata",
                "0",
                "-map_chapters",
                "1",
                "-c",
                "copy",
                "-y",
                str(output_video),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"FFmpeg failed to write chapters to {source}: {exc.stderr}") from exc

            replace_source(source, output_video, "FFmpeg")

    @staticmethod
    def _read_duration_ms(ffprobe: str, source: Path) -> int:
        command = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(source),
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            duration = Decimal(result.stdout.strip())
        except (subprocess.CalledProcessError, InvalidOperation) as exc:
            raise RuntimeError(f"ffprobe could not read video duration for {source}") from exc
        if duration <= 0:
            raise ValueError(f"Video duration must be positive: {source}")
        return int((duration * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _to_milliseconds(chapter: Chapter) -> int:
        timecode = chapter.time
        return ((timecode.hours * 60 + timecode.minutes) * 60 + timecode.seconds) * 1000 + timecode.milliseconds

    @staticmethod
    def _escape_metadata(value: str) -> str:
        escaped = value.replace("\\", "\\\\")
        for character in ("=", ";", "#"):
            escaped = escaped.replace(character, f"\\{character}")
        return escaped.replace("\n", "\\\n").replace("\r", "\\\r")
