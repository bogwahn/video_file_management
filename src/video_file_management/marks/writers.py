from __future__ import annotations

from pathlib import Path

try:
    import xattr  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    xattr = None  # fallback for environments without xattr

from .protocols import VideoMarksFile


XATTR_CHAPTERS_KEY = "com.video_file_management.chapters"


class ChapterMetadataWriter:
    """Writes chapter metadata to a video file via xattr.

    The metadata value is the serialized chapters string.
    """

    def write(self, video_file_path: str, chapters: VideoMarksFile) -> None:
        path = Path(video_file_path)
        if not path.exists() or not path.is_file():
            return
        data = chapters.to_string().encode("utf-8")
        if xattr is None:
            return
        attrs = xattr.xattr(str(path))
        attrs[XATTR_CHAPTERS_KEY] = data 