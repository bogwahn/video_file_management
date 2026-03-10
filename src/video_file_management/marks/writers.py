from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, MutableMapping, cast

from ..utils.timecode import format_timecode
from .protocols import VideoMarksFile

try:
    import xattr as _xattr  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    _xattr = None  # fallback for environments without xattr
xattr = cast(Any, _xattr)

XATTR_CHAPTERS_KEY = "com.video_file_management.chapters"


class ChapterMetadataWriter:
    """Writes chapter metadata to a video file via xattr.

    The metadata value is the serialized chapters string.
    """

    def write(self, video_file_path: str, chapters: VideoMarksFile) -> None:
        path = Path(video_file_path)
        if not path.exists() or not path.is_file():
            return
        text_value = chapters.to_string()
        if xattr is not None:
            data = text_value.encode("utf-8")
            attrs = cast(MutableMapping[str, bytes], xattr.xattr(str(path)))
            attrs[XATTR_CHAPTERS_KEY] = data
            return
        # Fallback to macOS CLI
        try:
            subprocess.run(
                [
                    "xattr",
                    "-w",
                    XATTR_CHAPTERS_KEY,
                    text_value,
                    str(path),
                ],
                check=True,
                capture_output=True,
            )
        except Exception:
            # Swallow errors to keep writer non-throwing
            return


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


def _replace_original(temp_result: Path, src: Path) -> None:
    """Atomically replace source file with chaptered output."""
    backup = src.with_suffix(src.suffix + ".bak")
    try:
        if backup.exists():
            backup.unlink()
        src.replace(backup)
        temp_result.replace(src)
        try:
            backup.unlink()
        except Exception:
            pass
    except Exception:
        if backup.exists() and not src.exists():
            backup.replace(src)


class MP4ChaptersWriter:
    """Embed chapters into MP4 using MP4Box (Nero iTunes-style chapters).

    Steps:
      1) Strip any existing chapters from input using ffmpeg (-map_chapters -1)
      2) Convert marks to Nero format and import with MP4Box -chap
    """

    def write(
        self,
        video_file_path: str,
        chapters: VideoMarksFile,
        output_path: str | None = None,
    ) -> None:
        mp4box = shutil.which("MP4Box")
        if not mp4box:
            return  # MP4Box not available
        src = Path(video_file_path)
        if not src.exists() or not src.is_file():
            return
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            cleaned = td_path / "clean.mp4"
            nero_txt = td_path / "chapters.txt"
            out_path = td_path / "out.mp4"

            # 1) Strip existing chapters (keep streams intact)
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        str(src),
                        "-map",
                        "0",
                        "-map_chapters",
                        "-1",
                        "-c",
                        "copy",
                        "-y",
                        str(cleaned),
                    ],
                    check=True,
                )
            except Exception:
                return

            # 2) Write Nero chapters file
            nero_txt.write_text(
                generate_nero_chapters_text(chapters),
                encoding="utf-8",
            )

            # 3) Import with MP4Box
            try:
                subprocess.run(
                    [
                        mp4box,
                        "-add",
                        str(cleaned),
                        "-chap",
                        str(nero_txt),
                        "-new",
                        str(out_path),
                    ],
                    check=True,
                    capture_output=True,
                )
            except Exception:
                return

            # 4) Place output at destination
            if output_path:
                shutil.copy2(str(out_path), output_path)
            else:
                _replace_original(out_path, src)
