"""Unit tests for post-download resolution enrichment (ffprobe via metadata_reader)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from video_file_management.zephyr.enrich import apply_resolution_enrichment, enrich_parsed_with_probe
from video_file_management.zephyr.parser import parse_filename


def test_enrich_skips_when_resolution_present(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "Jane.Doe.Bang.Scene.Title.4k.mp4"
    path.write_bytes(b"x")
    parsed = parse_filename(path.name)
    called = {"n": 0}

    def boom(_path):  # pragma: no cover - should not run
        called["n"] += 1
        raise AssertionError("should not probe when resolution present")

    monkeypatch.setattr("video_file_management.zephyr.enrich.read_file_metadata", boom)
    assert enrich_parsed_with_probe(path, parsed) is None
    assert called["n"] == 0


def test_enrich_probes_and_renames(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "Paris.White.NewSensations.Scene.Title.mp4"
    path.write_bytes(b"video")
    parsed = parse_filename(path.name)
    assert parsed.resolution is None

    def fake_meta(_path):
        return SimpleNamespace(
            video=SimpleNamespace(width=1920, height=1080),
            errors=[],
        )

    monkeypatch.setattr("video_file_management.zephyr.enrich.read_file_metadata", fake_meta)
    new_path, new_parsed, links = apply_resolution_enrichment(path, parsed)
    assert new_parsed.resolution == "1080p"
    assert new_path.name == "Paris.White.NewSensations.Scene.Title.1080p.mp4"
    assert new_path.is_file()
    assert not path.exists()
    assert links == ()


def test_enrich_noop_when_probe_fails(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "Jane.Doe.Studio.Title.mp4"
    path.write_bytes(b"x")
    parsed = parse_filename(path.name)

    def fake_meta(_path):
        return SimpleNamespace(
            video=SimpleNamespace(width=None, height=None),
            errors=["ffprobe not found in PATH"],
        )

    monkeypatch.setattr("video_file_management.zephyr.enrich.read_file_metadata", fake_meta)
    new_path, new_parsed, _ = apply_resolution_enrichment(path, parsed)
    assert new_path == path
    assert new_parsed.resolution is None
    assert path.exists()
