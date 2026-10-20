from pathlib import Path

import pytest

from video_file_management.videomarks.models import (
    Bookmark,
    BookmarksFile,
    BookmarksFileReader,
    BookmarksFileWriter,
    Chapter,
    ChaptersFile,
    ChaptersFileReader,
    ChaptersFileWriter,
    TimeCode,
)


def test_bookmark_reader_ignores_blank_lines_and_writer_serializes(tmp_path: Path) -> None:
    file_path = tmp_path / "movie.bookmarks.txt"
    file_path.write_text("\n00:00:01.250, Opening\n\n00:00:02.500, Ending\n", encoding="utf-8")

    bookmarks = BookmarksFileReader(str(file_path)).read()
    output_path = tmp_path / "output.bookmarks.txt"
    BookmarksFileWriter(str(output_path)).write(bookmarks)

    assert [bookmark.to_string() for bookmark in bookmarks.Bookmarks] == [
        "00:00:01.250,Opening",
        "00:00:02.500,Ending",
    ]
    assert output_path.read_text(encoding="utf-8") == "00:00:01.250,Opening\n00:00:02.500,Ending"


def test_chapter_reader_ignores_blank_lines_and_writer_serializes(tmp_path: Path) -> None:
    file_path = tmp_path / "movie.chapters.txt"
    file_path.write_text("\n[00:00:01.250] Opening\n\n[00:00:02.500] Ending\n", encoding="utf-8")

    chapters = ChaptersFileReader(str(file_path)).read()
    output_path = tmp_path / "output.chapters.txt"
    ChaptersFileWriter(str(output_path)).write(chapters)

    assert [chapter.to_string() for chapter in chapters.Chapters] == [
        "[00:00:01.250] Opening",
        "[00:00:02.500] Ending",
    ]
    assert output_path.read_text(encoding="utf-8") == "[00:00:01.250] Opening\n[00:00:02.500] Ending"


@pytest.mark.parametrize(
    ("reader_type", "malformed_line"),
    [
        (BookmarksFileReader, "00:00:bad,Opening"),
        (ChaptersFileReader, "[00:00:bad] Opening"),
    ],
)
def test_readers_report_line_number_for_malformed_marks(
    tmp_path: Path,
    reader_type: type[BookmarksFileReader] | type[ChaptersFileReader],
    malformed_line: str,
) -> None:
    file_path = tmp_path / "malformed.txt"
    file_path.write_text(f"\n{malformed_line}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        reader_type(str(file_path)).read()


def test_mark_file_models_serialize_their_specific_mark_types() -> None:
    bookmarks = BookmarksFile([Bookmark(TimeCode.from_string("00:00:01.000"), "Bookmark")])
    chapters = ChaptersFile([Chapter(TimeCode.from_string("00:00:02.000"), "Chapter")])

    assert bookmarks.to_string() == "00:00:01.000,Bookmark"
    assert chapters.to_string() == "[00:00:02.000] Chapter"
