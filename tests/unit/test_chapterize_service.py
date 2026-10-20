from pathlib import Path

import pytest

from video_file_management.chapterize.chapterize_service import ChapterizeService
from video_file_management.videomarks.models import Chapter, ChaptersFile, TimeCode


class RecordingChapterWriter:
    def __init__(self) -> None:
        self.writes: list[tuple[Path, ChaptersFile]] = []

    def write(self, video_path: Path, chapters: ChaptersFile) -> None:
        self.writes.append((video_path, chapters))


def write_marks(path: Path, marks: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(marks), encoding="utf-8")


def test_prefers_chapters_file_and_does_not_merge_bookmarks(tmp_path: Path) -> None:
    video = tmp_path / "video" / "Example Movie.mp4"
    video.parent.mkdir()
    video.touch()
    chapter_file = tmp_path / "icloud" / "Personal" / "Zetc" / "Chapters" / "Example Movie.txt"
    bookmark_file = tmp_path / "icloud" / "Personal" / "Zetc" / "Bookmarks" / "Example Movie-bookmarks.txt"
    write_marks(chapter_file, ["[00:00:01.000] Chapter only"])
    write_marks(bookmark_file, ["00:00:02.000,Bookmark only"])
    writer = RecordingChapterWriter()
    service = ChapterizeService(tmp_path / "icloud", writer)

    service.chapterize(video)

    assert len(writer.writes) == 1
    assert writer.writes[0][0] == video
    assert [chapter.to_string() for chapter in writer.writes[0][1].Chapters] == [
        Chapter(TimeCode.from_string("00:00:01.000"), "Chapter only").to_string()
    ]


def test_uses_bookmarks_as_chapters_when_chapters_file_is_missing(tmp_path: Path) -> None:
    video = tmp_path / "video" / "Example Movie.mp4"
    video.parent.mkdir()
    video.touch()
    bookmark_file = tmp_path / "icloud" / "Personal" / "Zetc" / "Bookmarks" / "Example Movie-bookmarks.txt"
    write_marks(bookmark_file, ["00:00:02.000,Bookmark title"])
    writer = RecordingChapterWriter()
    service = ChapterizeService(tmp_path / "icloud", writer)

    service.chapterize(video)

    assert [chapter.to_string() for chapter in writer.writes[0][1].Chapters] == [
        Chapter(TimeCode.from_string("00:00:02.000"), "Bookmark title").to_string()
    ]


def test_reports_when_neither_matching_marks_file_exists(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    video = tmp_path / "video" / "Example Movie.mp4"
    video.parent.mkdir()
    video.touch()
    writer = RecordingChapterWriter()
    service = ChapterizeService(tmp_path / "icloud", writer)

    service.chapterize(video)

    assert writer.writes == []
    assert "no matching chapter or bookmark file was found" in capsys.readouterr().out.lower()


def test_empty_input_processes_current_directory_candidates_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "movie.mp4").touch()
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "nested.mp4").touch()
    monkeypatch.chdir(tmp_path)
    writer = RecordingChapterWriter()
    service = ChapterizeService(tmp_path / "icloud", writer)

    service.chapterize("")

    assert writer.writes == []
    output = capsys.readouterr().out
    assert "movie.mp4" in output
    assert "nested.mp4" not in output


def test_reports_when_directory_has_no_video_candidates(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    service = ChapterizeService(tmp_path, RecordingChapterWriter())

    service.chapterize(tmp_path)

    assert "no video candidates" in capsys.readouterr().out.lower()
