import json
from pathlib import Path
from types import SimpleNamespace

from video_file_management import metadata_reader as mr
from video_file_management import tag_reader


def test_read_basic_metadata_parses_runtime_and_resolution(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "sample.mp4"
    video.write_text("")

    sample = {
        "format": {"duration": "9.87"},
        "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
        "chapters": [
            {"start": "0", "tags": {"title": "Intro"}},
            {"start": "5.5", "tags": {"TITLE": "Scene 1"}},
        ],
    }

    monkeypatch.setattr(mr.shutil, "which", lambda _: "/usr/bin/ffprobe")
    monkeypatch.setattr(
        mr.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(stdout=json.dumps(sample)),
    )
    monkeypatch.setattr(
        tag_reader,
        "read_finder_tags",
        lambda _: SimpleNamespace(tags=["Scenes:Chapters", "Sample"], errors=[]),
    )

    meta = mr.read_basic_metadata(video)
    assert meta.runtime_seconds == 9.87
    assert meta.video.width == 1280 and meta.video.height == 720
    assert meta.chapters and [c.title for c in meta.chapters] == ["Intro", "Scene 1"]
    assert meta.tags == ["Scenes:Chapters", "Sample"]
    assert meta.errors == []


def test_read_basic_metadata_handles_missing_ffprobe(monkeypatch, tmp_path: Path) -> None:
    video = tmp_path / "sample.mp4"
    video.write_text("")

    monkeypatch.setattr(mr.shutil, "which", lambda _: None)
    meta = mr.read_basic_metadata(video)
    assert meta.runtime_seconds is None
    assert meta.errors
