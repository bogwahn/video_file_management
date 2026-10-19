"""Detection of chapterize input file kinds."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .config import VIDEO_EXTENSIONS


class FileKindDetectorLike(Protocol):
    def detect(self, path: Path) -> str: ...


class FileKindDetector:
    """Detect input kind as video, bookmarks, chapters, or unknown."""

    def detect(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return "unknown"

        if path.suffix.lower() in VIDEO_EXTENSIONS:
            return "video"

        if path.suffix.lower() != ".txt":
            return "unknown"

        if "bookmark" in path.name.lower():
            return "bookmarks"

        return self._detect_text_kind(path)

    def _detect_text_kind(self, path: Path) -> str:
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("//"):
                    continue
                if line.startswith("[") and "]" in line:
                    return "chapters"
                if "," in line and ":" in line:
                    return "bookmarks"
                return "unknown"
        except Exception:
            return "unknown"
        return "unknown"
