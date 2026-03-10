from pathlib import Path
from types import SimpleNamespace

from video_file_management import chapter_file_walker as cfw


def _patch_embed_stack(monkeypatch) -> None:
    monkeypatch.setattr(cfw, "_check_embed_tools", lambda: None)
    monkeypatch.setattr(cfw, "_embed_chapters_in_place", lambda *_, **__: (True, None))
    monkeypatch.setattr(cfw, "ensure_finder_tag", lambda *_, **__: (False, None))


def test_process_video_embeds_from_chapters(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "Movie.mp4"
    video.write_text("")

    chapters_dir = tmp_path / "Chapters"
    chapters_dir.mkdir()
    (chapters_dir / "Movie.txt").write_text("[00:00:01.000] Intro\n", encoding="utf-8")

    monkeypatch.setattr(
        cfw,
        "read_chapters",
        lambda *_: SimpleNamespace(chapters=[], errors=[]),
    )
    _patch_embed_stack(monkeypatch)

    chapters_index = cfw._build_name_index(chapters_dir)
    result = cfw._process_video(
        video,
        chapters_index=chapters_index,
        bookmarks_index={},
        tag="Scenes:Chapters",
        dry_run=False,
    )

    assert result.status == "embedded_chapters"
    assert result.chapters_path is not None


def test_process_video_embeds_from_bookmarks(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "Clip.mp4"
    video.write_text("")

    bookmarks_dir = tmp_path / "Bookmarks"
    bookmarks_dir.mkdir()
    (bookmarks_dir / "Clip-bookmarks.txt").write_text(
        "0:00:01.000,Intro\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cfw,
        "read_chapters",
        lambda *_: SimpleNamespace(chapters=[], errors=[]),
    )
    _patch_embed_stack(monkeypatch)

    bookmarks_index = cfw._build_name_index(bookmarks_dir)
    result = cfw._process_video(
        video,
        chapters_index={},
        bookmarks_index=bookmarks_index,
        tag="Scenes:Chapters",
        dry_run=False,
    )

    assert result.status == "embedded_bookmarks"
    assert result.bookmark_path is not None


def test_process_video_reports_no_match(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "Unknown.mp4"
    video.write_text("")

    monkeypatch.setattr(
        cfw,
        "read_chapters",
        lambda *_: SimpleNamespace(chapters=[], errors=[]),
    )

    result = cfw._process_video(
        video,
        chapters_index={},
        bookmarks_index={},
        tag="Scenes:Chapters",
        dry_run=False,
    )

    assert result.status == "no_match"
