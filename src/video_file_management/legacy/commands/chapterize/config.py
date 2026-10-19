"""Configuration constants and helpers for chapterize command."""

from __future__ import annotations

import os
from pathlib import Path

CONFIGURED_VIDEO_ROOTS: tuple[Path, ...] = (
    Path("/Volumes/Zetc/Models"),
    Path("/Volumes/Zetc/Studios"),
    Path("/Volumes/Zetc/Uncategorized"),
    Path("/Volumes/Zetc-1/Models"),
    Path("/Volumes/Zetc-1/Studios"),
    Path("/Volumes/Zetc-1/Uncategorized"),
    Path("/Volumes/Torrents/Complete/Zetc"),
    Path("/Volumes/TorrentsOld/Complete/Zetc"),
    Path("/Volumes/Internal"),
    Path("/Volumes/External"),
)

DEFAULT_CHAPTERS_DIR = (
    Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc" / "Chapters"
)

DEFAULT_BOOKMARKS_DIR = (
    Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc" / "Bookmarks"
)

VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".avi"}
RESOLUTION_TOKENS = {"2160p", "1080p", "720p", "480p", "4k", "8k", "uhd", "fhd", "hd"}
DASH_TRANSLATION = str.maketrans(
    {
        "-": " ",
        "\u2010": " ",
        "\u2011": " ",
        "\u2012": " ",
        "\u2013": " ",
        "\u2014": " ",
        "\u2015": " ",
    }
)
BOOKMARK_SUFFIX_TOKENS = {"bookmark", "bookmarks"}
MIN_TOKEN_OVERLAP = 0.60
MIN_FUZZY_RATIO = 0.86

ENV_VIDEO_ROOTS = "VFM_CHAPTERIZE_VIDEO_ROOTS"
ENV_CHAPTERS_DIR = "VFM_CHAPTERIZE_CHAPTERS_DIR"
ENV_BOOKMARKS_DIR = "VFM_CHAPTERIZE_BOOKMARKS_DIR"


def configured_video_roots() -> tuple[Path, ...]:
    raw = os.getenv(ENV_VIDEO_ROOTS, "")
    if not raw:
        return CONFIGURED_VIDEO_ROOTS
    parsed = tuple(Path(item).expanduser() for item in raw.split(os.pathsep) if item.strip())
    return parsed or CONFIGURED_VIDEO_ROOTS


def configured_chapters_dir() -> Path:
    raw = os.getenv(ENV_CHAPTERS_DIR, "")
    if not raw:
        return DEFAULT_CHAPTERS_DIR
    return Path(raw).expanduser()


def configured_bookmarks_dir() -> Path:
    raw = os.getenv(ENV_BOOKMARKS_DIR, "")
    if not raw:
        return DEFAULT_BOOKMARKS_DIR
    return Path(raw).expanduser()
