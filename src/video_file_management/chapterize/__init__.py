"""Chapterize module for adding chapters to video files."""

from .controller import ChapterizeController
from .discovery import RecursiveNASDiscovery
from .interfaces import (
    ChapterMergeStrategy,
    UserPromptStrategy,
    VideoDiscoveryStrategy,
)
from .ui import AppleScriptUserPrompt
from .writer import MP4ChaptersWriterAtomic

__all__ = [
    "ChapterizeController",
    "RecursiveNASDiscovery",
    "ChapterMergeStrategy",
    "UserPromptStrategy",
    "VideoDiscoveryStrategy",
    "AppleScriptUserPrompt",
    "MP4ChaptersWriterAtomic",
]
