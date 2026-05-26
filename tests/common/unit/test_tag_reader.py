import plistlib
from pathlib import Path
from types import SimpleNamespace

from video_file_management import tag_reader as tr


def test_read_finder_tags_via_cli(monkeypatch, tmp_path: Path) -> None:
    file_path = tmp_path / "file.mp4"
    file_path.write_text("")
    tags = ["Scenes:Chapters", "Sample"]
    plist_data = plistlib.dumps(tags, fmt=plistlib.FMT_BINARY)
    hex_str = plist_data.hex()

    monkeypatch.setattr(tr, "xattr", None)
    monkeypatch.setattr(
        tr.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(returncode=0, stdout=hex_str),
    )

    result = tr.read_finder_tags(file_path)
    assert result.tags == tags
    assert result.errors == []


def test_read_finder_tags_handles_error(monkeypatch, tmp_path: Path) -> None:
    file_path = tmp_path / "file.mp4"
    file_path.write_text("")

    def boom(*_, **__):
        raise RuntimeError("fail")

    monkeypatch.setattr(tr, "xattr", None)
    monkeypatch.setattr(tr.subprocess, "run", boom)

    result = tr.read_finder_tags(file_path)
    assert result.tags == []
    assert result.errors
