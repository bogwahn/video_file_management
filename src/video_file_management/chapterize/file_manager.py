from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from video_file_management.videomarks.models import (
    BookmarksFileReader,
    ChaptersFileReader,
)


class ChapterizeFileManager:
    """Find video candidates and their matching chapter or bookmark files."""

    VIDEO_EXTENSIONS = frozenset(
        {
            ".mp4",
            ".mkv",
            ".mov",
            ".m4v",
            ".avi",
            ".wmv",
            ".webm",
            ".mpg",
            ".mpeg",
            ".ts",
            ".m2ts",
        }
    )
    MARK_ROOT = Path("Personal") / "Zetc"
    RESOLUTION_PATTERN = re.compile(r"(?i)(?<![a-z0-9])(?:480p|540p|720p|1080p|2k|4k|5k|6k|7k|8k)(?![a-z0-9])")

    def __init__(self, icloud_root: str | Path) -> None:
        self._icloud_root = Path(icloud_root).expanduser()
        self._chapters_directory = self._icloud_root / self.MARK_ROOT / "Chapters"
        self._bookmarks_directory = self._icloud_root / self.MARK_ROOT / "Bookmarks"

    def video_candidates(self, input_path: str | Path | None = None) -> list[Path]:
        """Return a single video file or direct video children of a directory."""
        target = Path.cwd() if input_path is None else Path(input_path).expanduser()
        if not target.exists():
            raise FileNotFoundError(target)

        if target.is_file():
            return [target.absolute()] if target.suffix.casefold() in self.VIDEO_EXTENSIONS else []

        return sorted(
            (
                path.absolute()
                for path in target.iterdir()
                if path.is_file() and path.suffix.casefold() in self.VIDEO_EXTENSIONS
            ),
            key=lambda path: path.name.casefold(),
        )

    def find_chapters_file(self, video_path: str | Path) -> Path | None:
        """Find the matching chapter file, applying the duplicate-mark threshold."""
        video_name = self._normalized_name(Path(video_path).stem)
        matches = self._matching_files(self._chapters_directory, video_name, bookmarks=False)
        return self._select_match(matches, bookmarks=False)

    def find_bookmarks_file(self, video_path: str | Path) -> Path | None:
        """Find the matching bookmark file, applying the duplicate-mark threshold."""
        video_name = self._normalized_name(Path(video_path).stem)
        matches = self._matching_files(self._bookmarks_directory, video_name, bookmarks=True)
        return self._select_match(matches, bookmarks=True)

    def _matching_files(self, directory: Path, video_name: str, *, bookmarks: bool) -> list[Path]:
        if not directory.is_dir():
            return []

        return sorted(
            (
                path
                for path in directory.iterdir()
                if path.is_file() and self._normalized_name(path.stem, bookmarks=bookmarks) == video_name
            ),
            key=lambda path: path.name.casefold(),
        )

    @staticmethod
    def _select_match(matches: Iterable[Path], *, bookmarks: bool) -> Path | None:
        candidates = list(matches)
        if len(candidates) == 1:
            return candidates[0]

        for candidate in candidates:
            if bookmarks:
                mark_count = len(BookmarksFileReader(str(candidate)).read().Bookmarks)
            else:
                mark_count = len(ChaptersFileReader(str(candidate)).read().Chapters)
            if mark_count >= 3:
                return candidate
        return None

    @classmethod
    def _normalized_name(cls, name: str, *, bookmarks: bool = False) -> str:
        normalized = cls.RESOLUTION_PATTERN.sub("", name).strip()
        normalized = re.sub(r"\(\s*\)", "", normalized)
        if bookmarks:
            normalized = re.sub(r"(?i)-bookmarks$", "", normalized).strip()
        normalized = re.sub(r"[\s._-]+", " ", normalized)
        return normalized.strip().casefold()
