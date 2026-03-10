"""CLI interface for chapterize command (used by Quick Action)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence, Iterable

from .controller import ChapterizeController
from .services import ChaptersLocatorService

# A simple fallback for BookmarksFileReader and ChaptersFileReader. 
# They read the file and return an object with a .marks() method.
from ..marks.bookmarks_reader import BookmarksFileReader
from ..marks.readers import ChaptersFileReader
from .writer import MP4ChaptersWriterAtomic
from ..marks.models import VideoMark
from ..marks.protocols import VideoMarksFile
from ..metadata_reader import read_file_metadata
from ..marks.chapters_file import ChaptersFile
from ..utils.timecode import format_timecode
from datetime import timedelta

# --- Minimal Protocol Implementations for CLI ---

import subprocess
from .discovery import RecursiveNASDiscovery

class CLIUserPromptStrategy:
    """Non-interactive prompt strategy for CLI."""
    def prompt_resolution(self, existing: Iterable[VideoMark], new: Iterable[VideoMark], merged: Iterable[VideoMark]) -> str:
        # For an automated Quick Action, 'Replace' is usually the safest non-interactive default.
        return "Replace"

    def _notify(self, message: str) -> None:
        try:
            escaped_message = message.replace('"', '\\"')
            # subprocess.run(
            #     [
            #         "/usr/bin/osascript",
            #         "-e",
            #         f'display notification "{escaped_message}" with title "Chapterize Video"',
            #     ],
            #     check=False,
            #     capture_output=True,
            # )
            pass
        except Exception:
            pass

    def notify_progress(self, message: str) -> None:
        print(message)
        if "complete" in message.lower():
            self._notify("Chapterize Complete!")

    def notify_error(self, message: str) -> None:
        print(f"ERROR: {message}", file=sys.stderr)
        try:
            escaped_message = message.replace('"', '\\"')
            # subprocess.run(
            #     [
            #         "/usr/bin/osascript",
            #         "-e",
            #         f'display alert "Chapterize Failed" message "{escaped_message}" as critical',
            #     ],
            #     check=False,
            #     capture_output=True,
            # )
            pass
        except Exception:
            pass
        sys.exit(1)

        
class CLIMarksReaderStrategy:
    """Reads marks using the appropriate reader for text bookmarks."""
    def read(self, file_path: str) -> VideoMarksFile:
        p = Path(file_path)
        if "bookmark" in p.name.lower():
            return BookmarksFileReader().read(str(p))
        else:
            return ChaptersFileReader().read(str(p))

class CLIVideoReaderStrategy:
    """Reads existing chapters from a video file."""
    def read(self, file_path: str) -> VideoMarksFile:
        chapters_file = ChaptersFile(file_path=file_path)
        meta = read_file_metadata(Path(file_path))
        for chapter in meta.chapters:
            td = timedelta(seconds=chapter.start_seconds)
            tc_str = format_timecode(td)
            chapters_file.add(tc_str, chapter.title)
        return chapters_file

class CLIVideoWriterStrategy:
    """Writes marks using MP4ChaptersWriterAtomic natively."""
    def __init__(self, prompt: CLIUserPromptStrategy) -> None:
        self.prompt = prompt
        
    def write(self, video_path: str, marks: Iterable[VideoMark]) -> None:
        writer = MP4ChaptersWriterAtomic(self.prompt)
        writer.write(video_path, marks)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry point for chapterize CLI.

    Args:
        argv: Command-line arguments.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="chapterize",
        description="Add chapters to video files from a bookmarks file",
    )
    parser.add_argument(
        "bookmark_path",
        help="Path to the bookmarks text file",
    )
    args = parser.parse_args(argv)

    bookmark_path = Path(args.bookmark_path)
    if not bookmark_path.exists() or not bookmark_path.is_file():
        print(f"Bookmarks file not found: {bookmark_path}", file=sys.stderr)
        return 1

    prompt = CLIUserPromptStrategy()
    controller = ChapterizeController(
        discovery=RecursiveNASDiscovery([
            "/Volumes/Zetc",
            "/Volumes/Zetc-1",
            "/Volumes/Torrents/Complete",
            "/Volumes/TorrentOld/Complete"
        ]),
        prompt=prompt,
        bookmarks_reader=CLIMarksReaderStrategy(),
        video_reader=CLIVideoReaderStrategy(),
        video_writer=CLIVideoWriterStrategy(prompt),
    )
    
    # Run the controller
    controller.run(str(bookmark_path))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
