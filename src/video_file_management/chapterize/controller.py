"""Controller orchestrating the Chapterize workflow."""

import logging
from typing import Iterable, Protocol

from video_file_management.chapterize.interfaces import (
    UserPromptStrategy,
    VideoDiscoveryStrategy,
)
from video_file_management.marks.models import VideoMark
from video_file_management.marks.protocols import VideoMarksFile

logger = logging.getLogger(__name__)


class VideoWriterStrategy(Protocol):
    """Protocol for embedding chapters into a video file."""

    def write(self, video_path: str, marks: Iterable[VideoMark]) -> None:
        """Writes the provided marks to the target video using atomic operations."""
        ...


class MarksReaderStrategy(Protocol):
    """Protocol for reading a marks file."""
    
    def read(self, file_path: str) -> VideoMarksFile:
        """Parses the file and returns a VideoMarksFile implementation."""
        ...


class ChapterizeController:
    """Orchestrates the Chapterize background workflow using dependency injection."""

    def __init__(
        self,
        discovery: VideoDiscoveryStrategy,
        prompt: UserPromptStrategy,
        bookmarks_reader: MarksReaderStrategy,
        video_reader: MarksReaderStrategy,  # Used to probe existing chapters
        video_writer: VideoWriterStrategy,
    ) -> None:
        self.discovery = discovery
        self.prompt = prompt
        self.bookmarks_reader = bookmarks_reader
        self.video_reader = video_reader
        self.video_writer = video_writer

    def _merge_marks(self, existing: Iterable[VideoMark], new: Iterable[VideoMark]) -> list[VideoMark]:
        """Simple strategy to merge two lists of marks chronologically."""
        all_marks = list(existing) + list(new)
        # Sort by timecode
        all_marks.sort(key=lambda m: m.timecode)
        
        # Deduplicate based on timecode and label (naive implementation for preview)
        unique_marks: list[VideoMark] = []
        for mark in all_marks:
            if not any(u for u in unique_marks if u.timecode == mark.timecode and u.label == mark.label):
                unique_marks.append(mark)
                
        return unique_marks

    def run(self, bookmark_path: str) -> None:
        """Executes the chapterize workflow."""
        try:
            self.prompt.notify_progress("Searching for video file...")
            video_path = self.discovery.find_video(bookmark_path)
            
            if not video_path:
                self.prompt.notify_error(f"Video file not found for bookmarks: {bookmark_path}")
                return

            self.prompt.notify_progress("Checking video for chapters...")
            
            # 1. Read bookmarks
            bookmarks = self.bookmarks_reader.read(bookmark_path)
            new_chapters = list(bookmarks.marks())
            if not new_chapters:
                self.prompt.notify_error("Bookmarks file is empty or invalid.")
                return

            # 2. Probe existing
            existing_chapters_file = self.video_reader.read(video_path)
            existing_chapters = list(existing_chapters_file.marks())
            
            final_chapters = new_chapters
            
            # 3. User Resolution if chapters exist
            if existing_chapters:
                merged_preview = self._merge_marks(existing_chapters, new_chapters)
                choice = self.prompt.prompt_resolution(
                    existing_chapters, new_chapters, merged_preview
                )
                
                if choice == "Keep":
                    return
                    
                if choice == "Merge":
                    final_chapters = merged_preview
                
                # If "Replace", final_chapters remains new_chapters
            
            # 4. Write
            self.prompt.notify_progress("Embedding finalized chapters...")
            self.video_writer.write(video_path, final_chapters)
            
            self.prompt.notify_progress("Chapterize complete!")
            
        except Exception as e:
            logger.exception("Error during chapterize run.")
            self.prompt.notify_error(f"An unexpected error occurred:\n{e}")
