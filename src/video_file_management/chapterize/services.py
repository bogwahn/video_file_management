"""Service implementations for chapterize operations."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from ..marks.bookmarks_reader import BookmarksFileReader
from ..marks.protocols import VideoMarksFile
from ..marks.readers import ChaptersFileReader
from ..marks.writers import MP4ChaptersWriter

DEFAULT_CHAPTERS_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "Personal"
    / "Zetc"
    / "Chapters"
)


class ChaptersLocatorService:
    """Locates chapters files for video files.

    Searches for chapters or bookmarks files that correspond to
    a given video file in a specified directory.
    """

    def __init__(self, chapters_dir: Path = DEFAULT_CHAPTERS_DIR) -> None:
        """Initialize the locator service.

        Args:
            chapters_dir: Directory to search for chapters files.
        """
        self.chapters_dir = chapters_dir

    def locate(self, video_path: Path) -> Optional[Path]:
        """Locate a chapters file for the given video.

        Strategy:
        - Exact match: `<stem>.txt`
        - Substring (case-insensitive) first-match fallback

        Args:
            video_path: Path to the video file.

        Returns:
            Path to the chapters file if found, None otherwise.
        """
        stem = video_path.stem
        if not self.chapters_dir.exists() or not self.chapters_dir.is_dir():
            return None

        # Try exact match first
        exact = self.chapters_dir / f"{stem}.txt"
        if exact.exists():
            return exact

        # Fallback: simple substring search (case-insensitive)
        lower_stem = stem.lower()
        for p in self.chapters_dir.iterdir():
            if not p.is_file():
                continue
            if lower_stem in p.name.lower():
                return p
        return None


class VideoConverterService:
    """Converts video files to MP4 format.

    Handles conversion/remuxing of various video formats to MP4
    for chapter embedding support.
    """

    def convert(self, source_path: Path, dest_path: Path) -> bool:
        """Convert/remux a video file to MP4 format.

        Attempts remuxing with `-c copy` first to avoid re-encoding.
        If that fails, falls back to re-encoding with libx264/aac.

        Args:
            source_path: Path to the source video file.
            dest_path: Path where the MP4 output should be written.

        Returns:
            True if conversion succeeded, False otherwise.
        """
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return False

        # Try remux (fast, no re-encode)
        cmd_copy = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_path),
            "-c",
            "copy",
            "-y",
            str(dest_path),
        ]
        try:
            subprocess.run(cmd_copy, check=True, capture_output=True)
            return True
        except Exception:
            pass

        # Fall back to re-encode
        cmd_reencode = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_path),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-y",
            str(dest_path),
        ]
        try:
            subprocess.run(cmd_reencode, check=True, capture_output=True)
            return True
        except Exception:
            return False


class ChaptersReaderFactoryImpl:
    """Factory for creating appropriate chapters readers.

    Determines the correct reader type based on file name patterns
    and creates the appropriate reader instance.
    """

    def create_reader(self, chapters_path: Path) -> Optional[VideoMarksFile]:
        """Create and return a reader for the given chapters file.

        Files with 'bookmark' in the name use BookmarksFileReader.
        All other files use ChaptersFileReader.

        Args:
            chapters_path: Path to the chapters file.

        Returns:
            A VideoMarksFile reader instance if the file can be read,
            None if the file doesn't exist.
        """
        if not chapters_path.exists():
            return None

        # Determine reader type based on filename
        if "bookmark" in chapters_path.name.lower():
            return BookmarksFileReader().read(str(chapters_path))
        else:
            return ChaptersFileReader().read(str(chapters_path))


class ChaptersEmbedderService:
    """Embeds chapters into video files.

    Orchestrates reading chapters from a file and writing them
    to a video file using the appropriate reader and writer.
    """

    def __init__(
        self,
        reader_factory: ChaptersReaderFactoryImpl,
        writer: MP4ChaptersWriter,
    ) -> None:
        """Initialize the embedder service.

        Args:
            reader_factory: Factory for creating chapters readers.
            writer: Writer for embedding chapters into MP4 files.
        """
        self._reader_factory = reader_factory
        self._writer = writer

    def embed(
        self, video_path: Path, chapters_path: Path, dry_run: bool = False
    ) -> bool:
        """Embed chapters from a chapters file into a video.

        Args:
            video_path: Path to the video file.
            chapters_path: Path to the chapters file.
            dry_run: If True, validate only without writing.

        Returns:
            True if embedding succeeded (or would succeed in dry_run),
            False otherwise.
        """
        # Read chapters using factory
        chapters = self._reader_factory.create_reader(chapters_path)
        if chapters is None:
            return False

        # Check if there are any chapters to embed
        if not list(chapters.marks()):
            return False

        # In dry-run mode, just validate we can read chapters
        if dry_run:
            return True

        # Embed chapters into video
        try:
            self._writer.write(str(video_path), chapters)
            return True
        except Exception:
            return False
