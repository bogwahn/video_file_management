from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="module", autouse=True)
def require_media_tools() -> None:
    for tool in ("ffmpeg", "ffprobe", "MP4Box"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} not available")


def test_chapterize_command_help() -> None:
    env = os.environ.copy()
    env["PATH"] = f"{Path.home() / 'bin'}:{env.get('PATH', '')}"
    result = subprocess.run(
        ["chapterize", "--help"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Apply chapters to video files" in result.stdout


@pytest.fixture
def chapterize_env(tmp_path: Path) -> dict[str, Path]:
    videos_dir = tmp_path / "videos"
    chapters_dir = tmp_path / "chapters"
    bookmarks_dir = tmp_path / "bookmarks"

    videos_dir.mkdir(parents=True)
    chapters_dir.mkdir(parents=True)
    bookmarks_dir.mkdir(parents=True)

    return {
        "videos": videos_dir,
        "chapters": chapters_dir,
        "bookmarks": bookmarks_dir,
    }


def _make_video(path: Path, *, with_chapters: bool = False) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-y",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    if not with_chapters:
        return

    metadata = path.with_suffix(".ffmeta")
    metadata.write_text(
        """;FFMETADATA1
[CHAPTER]
TIMEBASE=1/1000
START=0
END=500
title=Existing Chapter
""",
        encoding="utf-8",
    )
    with_chapter_path = path.with_name(f"{path.stem}.withchap{path.suffix}")

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-i",
            str(metadata),
            "-map_metadata",
            "1",
            "-codec",
            "copy",
            "-y",
            str(with_chapter_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    with_chapter_path.replace(path)
    metadata.unlink(missing_ok=True)


def _write_chapters_file(path: Path, title: str) -> None:
    path.write_text(f"[00:00:00.000] {title}\n", encoding="utf-8")


def _write_bookmarks_file(path: Path, title: str) -> None:
    path.write_text(f"00:00:00.000,{title}\n", encoding="utf-8")


def _run_cli(selected_path: Path, env_paths: dict[str, Path]) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{Path.home() / 'bin'}:{env.get('PATH', '')}"
    env["VFM_CHAPTERIZE_VIDEO_ROOTS"] = str(env_paths["videos"])
    env["VFM_CHAPTERIZE_CHAPTERS_DIR"] = str(env_paths["chapters"])
    env["VFM_CHAPTERIZE_BOOKMARKS_DIR"] = str(env_paths["bookmarks"])

    result = subprocess.run(
        ["chapterize", "--non-interactive", str(selected_path)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def _chapter_titles(path: Path) -> list[str]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_chapters",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout or "{}")
    chapters = data.get("chapters", []) or []
    titles: list[str] = []
    for chapter in chapters:
        tags = chapter.get("tags") if isinstance(chapter, dict) else None
        if isinstance(tags, dict):
            title = tags.get("title") or tags.get("TITLE")
            if isinstance(title, str):
                titles.append(title)
    return titles


def test_video_without_chapters_and_no_matching_marks_is_skipped(chapterize_env: dict[str, Path]) -> None:
    video = chapterize_env["videos"] / "NoMarks.NoChapters.1080p.mp4"
    _make_video(video, with_chapters=False)

    rc, out, _ = _run_cli(video, chapterize_env)

    assert rc == 1
    assert "skipped:" in out
    assert "no matching chapters/bookmarks found" in out


def test_video_with_chapters_and_no_matching_marks_is_skipped(chapterize_env: dict[str, Path]) -> None:
    video = chapterize_env["videos"] / "NoMarks.WithChapters.1080p.mp4"
    _make_video(video, with_chapters=True)

    rc, out, _ = _run_cli(video, chapterize_env)

    assert rc == 1
    assert "skipped:" in out
    assert "no matching chapters/bookmarks found" in out


def test_video_selected_with_matching_chapter_file_is_processed(chapterize_env: dict[str, Path]) -> None:
    video = chapterize_env["videos"] / "VideoMatchChapter.1080p.mp4"
    _make_video(video, with_chapters=False)

    chapters_file = chapterize_env["chapters"] / "VideoMatchChapter.1080p.txt"
    _write_chapters_file(chapters_file, "From Chapter File")

    rc, out, err = _run_cli(video, chapterize_env)

    assert rc == 0, err
    assert "processed:" in out
    assert "chapters written and verified" in out
    assert "From Chapter File" in _chapter_titles(video)


def test_video_selected_with_matching_bookmark_file_is_processed(chapterize_env: dict[str, Path]) -> None:
    video = chapterize_env["videos"] / "VideoMatchBookmark.1080p.mp4"
    _make_video(video, with_chapters=False)

    bookmark_file = chapterize_env["bookmarks"] / "VideoMatchBookmark.1080p-bookmarks.txt"
    _write_bookmarks_file(bookmark_file, "From Bookmark File")

    rc, out, err = _run_cli(video, chapterize_env)

    assert rc == 0, err
    assert "processed:" in out
    assert "chapters written and verified" in out
    assert "From Bookmark File" in _chapter_titles(video)


def test_chapter_file_selected_without_matching_video_is_skipped(chapterize_env: dict[str, Path]) -> None:
    chapter_file = chapterize_env["chapters"] / "NoVideoForChapter.1080p.txt"
    _write_chapters_file(chapter_file, "No Match")

    rc, out, _ = _run_cli(chapter_file, chapterize_env)

    assert rc == 1
    assert "skipped:" in out
    assert "no matching video found in configured roots" in out


def test_chapter_file_selected_with_matching_video_is_processed(chapterize_env: dict[str, Path]) -> None:
    video = chapterize_env["videos"] / "ChapterInputHasVideo.1080p.mp4"
    _make_video(video, with_chapters=False)

    chapter_file = chapterize_env["chapters"] / "ChapterInputHasVideo.1080p.txt"
    _write_chapters_file(chapter_file, "Chapter Input Success")

    rc, out, err = _run_cli(chapter_file, chapterize_env)

    assert rc == 0, err
    assert "processed:" in out
    assert "chapters written and verified" in out
    assert "Chapter Input Success" in _chapter_titles(video)


def test_bookmark_file_selected_without_matching_video_is_skipped(chapterize_env: dict[str, Path]) -> None:
    bookmark_file = chapterize_env["bookmarks"] / "NoVideoForBookmark-bookmarks.txt"
    _write_bookmarks_file(bookmark_file, "No Match")

    rc, out, _ = _run_cli(bookmark_file, chapterize_env)

    assert rc == 1
    assert "skipped:" in out
    assert "no matching video found in configured roots" in out


def test_bookmark_file_selected_with_matching_video_is_processed(chapterize_env: dict[str, Path]) -> None:
    video = chapterize_env["videos"] / "BookmarkInputHasVideo.1080p.mp4"
    _make_video(video, with_chapters=False)

    bookmark_file = chapterize_env["bookmarks"] / "BookmarkInputHasVideo.1080p-bookmarks.txt"
    _write_bookmarks_file(bookmark_file, "Bookmark Input Success")

    rc, out, err = _run_cli(bookmark_file, chapterize_env)

    assert rc == 0, err
    assert "processed:" in out
    assert "chapters written and verified" in out
    assert "Bookmark Input Success" in _chapter_titles(video)
