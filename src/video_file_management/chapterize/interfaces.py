"""Core interfaces for the Chapterize Video feature."""

from __future__ import annotations

from typing import Iterable, Protocol

from video_file_management.marks.models import VideoMark


class VideoDiscoveryStrategy(Protocol):
    """Strategy for locating a target video file based on a reference name."""

    def find_video(self, bookmark_path: str) -> str | None:
        """Locates the associated video file for a given bookmark file.

        Args:
            bookmark_path: The absolute path to the bookmarks file.

        Returns:
            The absolute path to the discovered video file, or None if not found.
        """
        ...


class UserPromptStrategy(Protocol):
    """Strategy for prompting the user for conflict resolution."""

    def prompt_resolution(
        self,
        existing_chapters: Iterable[VideoMark],
        new_chapters: Iterable[VideoMark],
        merged_preview: Iterable[VideoMark],
    ) -> str:
        """Presents a UI prompt to the user to choose a resolution path.

        Args:
            existing_chapters: Chapters currently embedded in the video.
            new_chapters: Chapters derived from the bookmarks file.
            merged_preview: A preview of what the combined chapters will look like.

        Returns:
            The user's choice, typically "Keep", "Replace", or "Merge".
        """
        ...

    def notify_progress(self, message: str) -> None:
        """Sends a transient, non-blocking notification to the user.

        Args:
            message: The message to display (e.g., "Searching for video...").
        """
        ...

    def notify_error(self, message: str) -> None:
        """Sends a robust error notification to the user and aborts.

        Args:
            message: The explicit error detailing what went wrong.
        """
        ...


class ChapterMergeStrategy(Protocol):
    """Strategy for merging two sets of marks."""

    def merge(
        self, existing: Iterable[VideoMark], new: Iterable[VideoMark]
    ) -> Iterable[VideoMark]:
        """Combines two sets of marks, resolving chronological overlaps.

        Args:
            existing: The current marks in the file.
            new: The new marks to inject.

        Returns:
            A chronologically sorted, merged list of VideoMarks.
        """
        ...
