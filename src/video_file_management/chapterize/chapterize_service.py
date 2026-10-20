from __future__ import annotations

from pathlib import Path

from video_file_management.videomarks.models import (
    Bookmark,
    BookmarksFileReader,
    Chapter,
    ChaptersFile,
    ChaptersFileReader,
)

from .chapter_track_writer import ChapterWriter
from .file_manager import ChapterizeFileManager


class ChapterizeService:
    """Select mark files and write the chosen marks into each candidate video."""

    def __init__(
        self,
        icloud_root: str | Path,
        chapter_writer: ChapterWriter,
    ) -> None:
        self._file_manager = ChapterizeFileManager(icloud_root)
        self._chapter_writer = chapter_writer

    def chapterize(self, input_path: str | Path | None = None) -> None:
        video_paths = self._file_manager.video_candidates(input_path)
        if not video_paths:
            target = Path.cwd() if input_path is None or input_path == "" else Path(input_path).expanduser()
            print(f"No video candidates found in {target}.")
            return

        for video_path in video_paths:
            chapters_path = self._file_manager.find_chapters_file(video_path)
            if chapters_path is not None:
                chapters = ChaptersFileReader(str(chapters_path)).read()
            else:
                bookmarks_path = self._file_manager.find_bookmarks_file(video_path)
                if bookmarks_path is None:
                    print(f"No matching chapter or bookmark file was found for {video_path.name}.")
                    continue
                bookmarks = BookmarksFileReader(str(bookmarks_path)).read()
                chapters = ChaptersFile(self._to_chapters(bookmarks.Bookmarks))

            self._chapter_writer.write(video_path, chapters)

    @staticmethod
    def _to_chapters(bookmarks: list[Bookmark]) -> list[Chapter]:
        return [Chapter(bookmark.time, bookmark.label) for bookmark in bookmarks]
