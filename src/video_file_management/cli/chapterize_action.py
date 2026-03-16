"""CLI entry point for the Chapterize Video feature."""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

from video_file_management.chapterize.controller import ChapterizeController
from video_file_management.chapterize.discovery import RecursiveNASDiscovery
from video_file_management.chapterize.ui import AppleScriptUserPrompt
from video_file_management.chapterize.writer import MP4ChaptersWriterAtomic
from video_file_management.marks.bookmarks_reader import BookmarksFileReader
from video_file_management.marks.chapters_file import ChaptersFile
from video_file_management.marks.protocols import VideoMarksFile
from video_file_management.metadata_reader import read_file_metadata
from video_file_management.utils.timecode import format_timecode


class VideoMetadataChapterReader:
    """Adapter to read existing chapters from a video file into a ChaptersFile.

    This implements MarksReaderStrategy for the Video File by leveraging
    the existing `metadata_reader` module.
    """

    def read(self, file_path: str) -> VideoMarksFile:
        chapters_file = ChaptersFile(file_path=file_path)
        meta = read_file_metadata(Path(file_path))

        for chapter in meta.chapters:
            # metadata_reader gives us float seconds. Convert to string HH:MM:SS.mmm
            td = timedelta(seconds=chapter.start_seconds)
            tc_str = format_timecode(td)
            chapters_file.add(tc_str, chapter.title)

        return chapters_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Chapterize video file using bookmarks.")
    parser.add_argument(
        "bookmark_file",
        help="Path to the bookmarks file.",
    )
    args = parser.parse_args()

    bookmark_path = Path(args.bookmark_file).absolute()

    if not bookmark_path.exists() or not bookmark_path.is_file():
        print(f"Error: Bookmark file not found at {bookmark_path}", file=sys.stderr)
        return 1

    # Configure our composition root
    # Target Synology NAS volumes over SMB/AFP mounts, plus local bookmark dir
    search_directories = [
        Path("/Volumes/Zetc"),
        Path("/Volumes/Zetc-1"),
        Path("/Volumes/Torrents/Complete"),
        Path("/Volumes/TorrentOld/Complete"),
        bookmark_path.parent,
    ]

    prompt_strategy = AppleScriptUserPrompt()
    discovery_strategy = RecursiveNASDiscovery(search_directories)
    writer_strategy = MP4ChaptersWriterAtomic(prompt_strategy)

    # Readers
    bookmarks_reader = BookmarksFileReader()
    video_reader = VideoMetadataChapterReader()

    # Wire up controller
    controller = ChapterizeController(
        discovery=discovery_strategy,
        prompt=prompt_strategy,
        bookmarks_reader=bookmarks_reader,
        video_reader=video_reader,
        video_writer=writer_strategy,
    )

    try:
        controller.run(str(bookmark_path))
        return 0
    except Exception as e:
        print(f"Fatal error executing chapterize workflow: {e}", file=sys.stderr)
        # Attempt to notify via UI if possible
        try:
            prompt_strategy.notify_error(f"Fatal error executing chapterize workflow:\n{e}")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
