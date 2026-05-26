from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, MutableMapping, cast

from ..chapter_reader import read_chapters
from ..metadata_reader import read_file_metadata
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

    Behavior:
        - Direct in-place writes (output_path is None) use MP4Box `-chap` against
            the source file to avoid creating a full temporary video copy.
        - Explicit output writes (output_path provided) preserve the older
            ffmpeg-clean + MP4Box-new flow used by copy-to-new-file workflows.
    """

    def write(
        self,
        video_file_path: str,
        chapters: VideoMarksFile,
        output_path: str | None = None,
    ) -> None:
        mp4box = shutil.which("MP4Box")
        if not mp4box:
            raise RuntimeError("MP4Box not available in PATH")
        src = Path(video_file_path)
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(video_file_path)

        expected_count = len(tuple(chapters.marks()))
        if expected_count == 0:
            raise RuntimeError("No chapters to write")

        # Fast path for chapterize CLI: mutate file in place without full copy.
        if output_path is None:
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                nero_txt = td_path / "chapters.txt"
                nero_txt.write_text(generate_nero_chapters_text(chapters), encoding="utf-8")
                try:
                    subprocess.run(
                        [
                            mp4box,
                            "-chap",
                            str(nero_txt),
                            str(src),
                        ],
                        check=True,
                        capture_output=True,
                    )
                except Exception as exc:
                    raise RuntimeError(f"MP4Box in-place write failed: {exc}") from exc

                verified, error = _verify_written_chapters(src, expected_count)
                if not verified:
                    raise RuntimeError(error or "Chapter verification failed")
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
            except Exception as exc:
                raise RuntimeError(f"MP4Box output write failed: {exc}") from exc

            # 4) Place output at destination
            shutil.copy2(str(out_path), output_path)
            verified, error = _verify_written_chapters(Path(output_path), expected_count)
            if not verified:
                raise RuntimeError(error or "Chapter verification failed")


def _verify_written_chapters(path: Path, expected_count: int) -> tuple[bool, str | None]:
    try:
        if path.stat().st_size <= 1024:
            return False, f"Output file is unexpectedly small ({path.stat().st_size} bytes)"
    except OSError as exc:
        return False, f"Unable to stat output file: {exc}"

    meta = read_file_metadata(path)
    has_video_stream = bool(meta.video.codec or meta.video.width or meta.video.height)
    if not has_video_stream:
        return False, "No video streams found after chapter write"

    result = read_chapters(path)
    if result.errors:
        return False, "; ".join(result.errors)
    if len(result.chapters) < expected_count:
        return False, f"Expected {expected_count} chapters but found {len(result.chapters)}"
    return True, None
