from __future__ import annotations

from collections.abc import Iterable

from .bookmark import Bookmark
from .videomarks_file_abc import VideoMarksFileABC


class BookmarksFile(VideoMarksFileABC):
    """Concrete marks container for bookmarks.

    Serializes as "HH:MM:SS.mmm,Label" lines.
    """

    def __init__(self, bookmarks: Iterable[Bookmark] = ()) -> None:
        super().__init__(bookmarks)

    @property
    def Bookmarks(self) -> list[Bookmark]:
        return [mark for mark in self._marks if isinstance(mark, Bookmark)]
