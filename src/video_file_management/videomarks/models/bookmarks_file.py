from __future__ import annotations

from collections.abc import Iterable

from .bookmark import Bookmark
from .videomark import VideoMark
from .videomarks_file_abc import VideoMarksFileABC


class BookmarksFile(VideoMarksFileABC):
    """Concrete marks container for bookmarks.

    Serializes as "HH:MM:SS.mmm,Label" lines.
    """

    def __init__(self, bookmarks: Iterable[Bookmark] = ()) -> None:
        marks = list(bookmarks)
        if any(not isinstance(mark, Bookmark) for mark in marks):
            raise TypeError("BookmarksFile only accepts Bookmark marks")
        super().__init__(marks)

    def addMark(self, videomark: VideoMark) -> None:
        if not isinstance(videomark, Bookmark):
            raise TypeError("BookmarksFile only accepts Bookmark marks")
        super().addMark(videomark)

    @property
    def Bookmarks(self) -> list[Bookmark]:
        return [mark for mark in self._marks if isinstance(mark, Bookmark)]
