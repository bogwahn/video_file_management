"""File readers."""

from .bookmarks_file_reader import BookmarksFileReader
from .chapters_file_reader import ChaptersFileReader
from .file_reader import FileReader

__all__ = ["FileReader", "ChaptersFileReader", "BookmarksFileReader"]
