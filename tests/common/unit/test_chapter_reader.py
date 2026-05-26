import json
from pathlib import Path
from types import SimpleNamespace

from video_file_management import chapter_reader as cr


def test_read_chapters_parses_titles(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_text("")

    sample = {
        "chapters": [
            {"start": "0", "tags": {"title": "Intro"}},
            {"start": "5.5", "tags": {"TITLE": "Scene 1"}},
        ]
    }

    monkeypatch.setattr(cr.shutil, "which", lambda _: "/usr/bin/ffprobe")
    monkeypatch.setattr(
        cr.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(stdout=json.dumps(sample)),
    )

    result = cr.read_chapters(video)
    assert [c.title for c in result.chapters] == ["Intro", "Scene 1"]
    assert [c.start_seconds for c in result.chapters] == [0.0, 5.5]
    assert result.errors == []


def test_read_chapters_handles_missing_ffprobe(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_text("")
    monkeypatch.setattr(cr.shutil, "which", lambda _: None)

    result = cr.read_chapters(video)
    assert result.chapters == []
    assert result.errors
