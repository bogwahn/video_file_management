from pathlib import Path

import pytest

from video_file_management.chapterize.file_manager import ChapterizeFileManager


@pytest.fixture
def mark_directories(tmp_path: Path) -> tuple[Path, Path, Path]:
    icloud_root = tmp_path / "icloud"
    chapters = icloud_root / "Personal" / "Zetc" / "Chapters"
    bookmarks = icloud_root / "Personal" / "Zetc" / "Bookmarks"
    chapters.mkdir(parents=True)
    bookmarks.mkdir(parents=True)
    return icloud_root, chapters, bookmarks


def test_video_candidates_use_nonrecursive_case_insensitive_extension_allowlist(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    videos = [
        "movie.MP4",
        "clip.mkv",
        "film.mov",
        "video.m4v",
        "old.avi",
        "show.wmv",
        "web.webm",
        "mpeg.mpg",
        "mpeg.mpeg",
        "stream.ts",
        "transport.m2ts",
    ]
    for name in videos:
        (tmp_path / name).touch()
    (tmp_path / "nested" / "nested.mp4").touch()
    (tmp_path / "notes.txt").touch()

    candidates = ChapterizeFileManager(tmp_path).video_candidates(tmp_path)

    assert [path.name for path in candidates] == sorted(videos, key=str.casefold)


def test_video_candidates_use_current_directory_for_empty_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "movie.mp4").touch()
    monkeypatch.chdir(tmp_path)
    manager = ChapterizeFileManager(tmp_path / "icloud")

    assert manager.video_candidates(None) == [tmp_path / "movie.mp4"]


@pytest.mark.parametrize("resolution", ["480p", "540p", "720p", "1080p", "2k", "4k", "5k", "6k", "7k", "8k"])
def test_chapter_name_matches_after_resolution_labels_are_removed(
    mark_directories: tuple[Path, Path, Path],
    resolution: str,
) -> None:
    icloud_root, chapters_dir, _ = mark_directories
    video_path = Path("/videos/Example Movie 1080p.mp4")
    chapter_path = chapters_dir / f"Example Movie {resolution}.txt"
    chapter_path.write_text("[00:00:01.000] Opening\n", encoding="utf-8")

    manager = ChapterizeFileManager(icloud_root)

    assert manager.find_chapters_file(video_path) == chapter_path


def test_bookmark_name_removes_suffix_and_resolution_labels(
    mark_directories: tuple[Path, Path, Path],
) -> None:
    icloud_root, _, bookmarks_dir = mark_directories
    video_path = Path("/videos/Example Movie 1080p.mp4")
    bookmark_path = bookmarks_dir / "Example Movie-bookmarks 4k.txt"
    bookmark_path.write_text("00:00:01.000,Opening\n", encoding="utf-8")

    manager = ChapterizeFileManager(icloud_root)

    assert manager.find_bookmarks_file(video_path) == bookmark_path


def test_resolution_labels_in_parentheses_are_removed_from_video_name(
    mark_directories: tuple[Path, Path, Path],
) -> None:
    icloud_root, chapters_dir, _ = mark_directories
    video_path = Path("/videos/Example Movie (1080p).mp4")
    chapter_path = chapters_dir / "Example Movie.txt"
    chapter_path.write_text("[00:00:01.000] Opening\n", encoding="utf-8")

    manager = ChapterizeFileManager(icloud_root)

    assert manager.find_chapters_file(video_path) == chapter_path


def test_single_exact_match_is_selected_even_with_fewer_than_three_marks(
    mark_directories: tuple[Path, Path, Path],
) -> None:
    icloud_root, chapters_dir, _ = mark_directories
    video_path = Path("/videos/Example Movie.mp4")
    chapter_path = chapters_dir / "Example Movie.txt"
    chapter_path.write_text("[00:00:01.000] Opening\n", encoding="utf-8")

    manager = ChapterizeFileManager(icloud_root)

    assert manager.find_chapters_file(video_path) == chapter_path


def test_multiple_exact_matches_select_first_sorted_candidate_with_three_marks(
    mark_directories: tuple[Path, Path, Path],
) -> None:
    icloud_root, chapters_dir, _ = mark_directories
    video_path = Path("/videos/Example Movie.mp4")
    (chapters_dir / "Example Movie 480p.txt").write_text(
        "[00:00:01.000] One\n[00:00:02.000] Two\n",
        encoding="utf-8",
    )
    expected = chapters_dir / "Example Movie 720p.txt"
    expected.write_text(
        "[00:00:01.000] One\n[00:00:02.000] Two\n[00:00:03.000] Three\n",
        encoding="utf-8",
    )
    (chapters_dir / "Example Movie 1080p.txt").write_text(
        "[00:00:01.000] One\n[00:00:02.000] Two\n",
        encoding="utf-8",
    )

    manager = ChapterizeFileManager(icloud_root)

    assert manager.find_chapters_file(video_path) == expected


def test_multiple_exact_matches_without_three_marks_return_no_match(
    mark_directories: tuple[Path, Path, Path],
) -> None:
    icloud_root, chapters_dir, _ = mark_directories
    video_path = Path("/videos/Example Movie.mp4")
    (chapters_dir / "Example Movie 480p.txt").write_text(
        "[00:00:01.000] One\n[00:00:02.000] Two\n",
        encoding="utf-8",
    )
    (chapters_dir / "Example Movie 720p.txt").write_text(
        "[00:00:01.000] One\n",
        encoding="utf-8",
    )

    manager = ChapterizeFileManager(icloud_root)

    assert manager.find_chapters_file(video_path) is None


def test_multiple_bookmark_matches_select_first_candidate_with_three_marks(
    mark_directories: tuple[Path, Path, Path],
) -> None:
    icloud_root, _, bookmarks_dir = mark_directories
    video_path = Path("/videos/Example Movie.mp4")
    (bookmarks_dir / "Example Movie-bookmarks 480p.txt").write_text(
        "00:00:01.000,One\n00:00:02.000,Two\n",
        encoding="utf-8",
    )
    expected = bookmarks_dir / "Example Movie-bookmarks 720p.txt"
    expected.write_text(
        "00:00:01.000,One\n00:00:02.000,Two\n00:00:03.000,Three\n",
        encoding="utf-8",
    )
    (bookmarks_dir / "Example Movie-bookmarks 1080p.txt").write_text(
        "00:00:01.000,One\n",
        encoding="utf-8",
    )

    manager = ChapterizeFileManager(icloud_root)

    assert manager.find_bookmarks_file(video_path) == expected
