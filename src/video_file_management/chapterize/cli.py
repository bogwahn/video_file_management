from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

from .chapter_track_writer import ChapterTrackWriter
from .chapterize_service import ChapterizeService


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write chapter marks into video files.")
    parser.add_argument("path", nargs="?", help="video file or directory; defaults to the current directory")
    args = parser.parse_args(argv)

    icloud_root = os.environ.get("icloud")
    if not icloud_root:
        parser.error("the icloud environment variable must point to the configured iCloud root")

    service = ChapterizeService(icloud_root, ChapterTrackWriter())
    service.chapterize(args.path)
    return 0
