"""Protocol definitions for chapterize services."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol

from ..marks.protocols import VideoMarksFile


class ChaptersLocator(Protocol):
    """Protocol for locating chapters files for video files.

    Implementations should search for chapters or bookmarks files
    that correspond to a given video file.
    """

    def locate(self, video_path: Path) -> Optional[Path]:
        """Locate a chapters file for the given video.

        Args:
            video_path: Path to the video file.

        Returns:
            Path to the chapters file if found, None otherwise.
        """
        ...


class VideoConverter(Protocol):
    """Protocol for converting video files to MP4 format.

    Implementations should handle conversion/remuxing of various
    video formats to MP4 for chapter embedding.
    """

    def convert(self, source_path: Path, dest_path: Path) -> bool:
        """Convert/remux a video file to MP4 format.

        Args:
            source_path: Path to the source video file.
            dest_path: Path where the MP4 output should be written.

        Returns:
            True if conversion succeeded, False otherwise.
        """
        ...


class ChaptersReaderFactory(Protocol):
    """Protocol for creating appropriate chapters readers.

    Implementations should determine the correct reader type
    based on the chapters file format or extension.
    """

    def create_reader(self, chapters_path: Path) -> Optional[VideoMarksFile]:
        """Create and return a reader for the given chapters file.

        Args:
            chapters_path: Path to the chapters file.

        Returns:
            A VideoMarksFile reader instance if the file can be read,
            None if the format is unsupported or file cannot be read.
        """
        ...


class ChaptersEmbedder(Protocol):
    """Protocol for embedding chapters into video files.

    Implementations should handle reading chapters from a file
    and writing them to a video file.
    """

    def embed(self, video_path: Path, chapters_path: Path, dry_run: bool = False) -> bool:
        """Embed chapters from a chapters file into a video.

        Args:
            video_path: Path to the video file.
            chapters_path: Path to the chapters file.
            dry_run: If True, perform validation only without writing.

        Returns:
            True if embedding succeeded (or would succeed in dry_run),
            False otherwise.
        """
        ...
