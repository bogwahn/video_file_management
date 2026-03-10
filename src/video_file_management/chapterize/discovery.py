"""Discovery strategies for the Chapterize Video feature."""

import os
from pathlib import Path
from typing import Sequence

from video_file_management.chapterize.interfaces import VideoDiscoveryStrategy


class RecursiveNASDiscovery(VideoDiscoveryStrategy):
    """Discovers a video file by recursively scanning configured NAS directories."""

    def __init__(self, search_directories: Sequence[str] | Sequence[Path]) -> None:
        """Initializes the discovery strategy with target directories.

        Args:
            search_directories: A list of absolute directory paths to search.
        """
        self.search_directories = [Path(d) for d in search_directories]
        self.video_extensions = {".mp4", ".mkv", ".mov", ".m4v", ".avi"}
        self.ignore_dirs = {"#Recycle Bin"}

    def _normalize_name(self, name: str) -> str:
        """Normalizes a filename stem for fuzzy matching (case-insensitive, dots/spaces/hyphens interchangeable)."""
        return name.lower().replace(".", " ").replace("_", " ").replace("-", " ").strip()

    def find_video(self, bookmark_path: str) -> str | None:
        """Recursively scans the configured directories for a video matching the bookmark stem.

        Uses fuzzy matching: ignores case and treats '.' and ' ' interchangeably.

        Args:
            bookmark_path: The path to the bookmark file (e.g. /path/to/movie.txt).

        Returns:
            The absolute path to the matching video file, or None if not found.
        """
        bookmark_file = Path(bookmark_path)
        raw_stem = bookmark_file.stem.replace("-bookmarks", "").replace("_bookmarks", "")
        normalized_target = self._normalize_name(raw_stem)

        # 1. Check local bookmark parent directory first just in case
        local_dir = bookmark_file.parent
        if local_dir.exists() and local_dir.is_dir():
            try:
                for child in local_dir.iterdir():
                    if child.is_file() and child.suffix.lower() in self.video_extensions:
                        if self._normalize_name(child.stem) == normalized_target:
                            return str(child.absolute())
            except OSError:
                pass

        # 2. Recursively search NAS targets
        for root_dir in self.search_directories:
            if not root_dir.exists() or not root_dir.is_dir():
                continue
                
            for currentpath, dirnames, filenames in os.walk(root_dir):
                # Modify dirnames in-place to prune excluded directories from the walk tree
                dirnames[:] = [d for d in dirnames if d not in self.ignore_dirs]

                for filename in filenames:
                    # Quick extension check before deeper string inspection
                    ext_lower = os.path.splitext(filename)[1].lower()
                    if ext_lower in self.video_extensions:
                        stem = os.path.splitext(filename)[0]
                        if self._normalize_name(stem) == normalized_target:
                            candidate = Path(currentpath) / filename
                            return str(candidate.absolute())

        return None
