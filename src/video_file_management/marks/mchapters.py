from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .protocols import VideoMarksFile

DEFAULT_LANGUAGE = "English"
DEFAULT_TIMESCALE = 1000


@dataclass(slots=True)
class MChaptersDocument:
    """Represents an mChapters-formatted document."""

    title: str
    language: str
    time_scale: int
    chapters: VideoMarksFile

    def to_string(self) -> str:
        lines: list[str] = [
            self.title,
            f"Language: {self.language}",
            "",
            f"<@TimeScale:{self.time_scale}>",
            "<@Start>",
        ]
        marks_text = self.chapters.to_string()
        if marks_text:
            lines.extend(marks_text.splitlines())
        lines.append("<@End>")
        return "\n".join(lines)


def build_title_from_path(bookmarks_path: Path) -> str:
    """Return a default title derived from a bookmarks file path."""
    name = bookmarks_path.name
    if name.endswith("-bookmarks.txt"):
        name = name[:-14]
    elif name.endswith(".txt"):
        name = name[:-4]
    return name


def create_mchapters_document(
    bookmarks_path: Path,
    chapters: VideoMarksFile,
    *,
    language: str = DEFAULT_LANGUAGE,
    time_scale: int = DEFAULT_TIMESCALE,
    title: str | None = None,
) -> MChaptersDocument:
    derived_title = title or build_title_from_path(bookmarks_path)
    return MChaptersDocument(
        title=derived_title,
        language=language,
        time_scale=time_scale,
        chapters=chapters,
    )
