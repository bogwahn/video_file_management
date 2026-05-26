from __future__ import annotations

from pathlib import Path

from video_file_management.chapterize.cli import (
    FileKindDetector,
    PathMatchIndex,
    VideoLocator,
    _normalize_name,
    collect_input_files,
)


def test_file_kind_detector_detects_bookmarks_by_content(tmp_path: Path) -> None:
    detector = FileKindDetector()
    path = tmp_path / "sample.txt"
    path.write_text("00:00:01.000,Intro\n", encoding="utf-8")

    assert detector.detect(path) == "bookmarks"


def test_path_match_index_prefers_chapters_over_bookmarks(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "chapters"
    bookmarks_dir = tmp_path / "bookmarks"
    chapters_dir.mkdir()
    bookmarks_dir.mkdir()

    chapter_file = chapters_dir / "My.Movie.1080p.txt"
    bookmark_file = bookmarks_dir / "My.Movie.1080p-bookmarks.txt"

    chapter_file.write_text("[00:00:00.000] Intro\n", encoding="utf-8")
    bookmark_file.write_text("00:00:00.000,Intro\n", encoding="utf-8")

    index = PathMatchIndex(chapters_dir=chapters_dir, bookmarks_dir=bookmarks_dir)
    match = index.find_marks_for_video_name("My.Movie.1080p")

    assert match is not None
    assert match[0] == chapter_file
    assert match[1] == "chapters"


def test_video_locator_finds_video_for_matching_marks_name(tmp_path: Path) -> None:
    root = tmp_path / "videos"
    root.mkdir()

    video = root / "Case.Match.1080p.mp4"
    video.write_bytes(b"fake")

    marks = tmp_path / "Case.Match.1080p-bookmarks.txt"
    marks.write_text("00:00:00.000,Intro\n", encoding="utf-8")

    locator = VideoLocator((root,))
    found = locator.find_video_for_marks_file(marks)

    assert found == video


def test_normalize_name_keeps_non_suffix_bookmark_word() -> None:
    assert _normalize_name("VideoMatchBookmark.1080p") == "videomatchbookmark"
    assert _normalize_name("VideoMatchBookmark.1080p-bookmarks") == "videomatchbookmark"


def test_collect_input_files_defaults_to_current_directory(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"video")
    monkeypatch.chdir(tmp_path)

    files = collect_input_files(())

    assert target.resolve() in files
