"""Watcher routing tests using temporary directories (no /Internal required)."""

from __future__ import annotations

from pathlib import Path

from video_file_management.zephyr.config import load_config
from video_file_management.zephyr.inventory import SqliteInventoryRepository
from video_file_management.zephyr.parser import parse_filename
from video_file_management.zephyr.watcher.daemon import process_file, scan_hot_folder
from video_file_management.zephyr.watcher.router import route_file


def _cfg(tmp_path: Path):
    hot = tmp_path / "Download"
    vr = tmp_path / "VR" / "{First.Actress}"
    non_vr = tmp_path / "Uncategorized"
    quarantine = tmp_path / "Quarantine"
    db = tmp_path / "inv.sqlite3"
    hot.mkdir()
    non_vr.mkdir()
    quarantine.mkdir()
    return load_config(
        data={
            "hot_folder": str(hot),
            "dest": {"vr": str(vr), "non_vr": str(non_vr)},
            "quarantine_folder": str(quarantine),
            "inventory_db": str(db),
            "stable_seconds": 0.2,
            "collision_policy": "leave_in_hot",
            "vr_secondary_link": "symlink",
        }
    )


def test_route_non_vr(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    name = "Jane.Doe.Bang.Scene.Title.4k.mp4"
    src = cfg.hot_folder / name
    src.write_bytes(b"video-bytes")
    parsed = parse_filename(name)
    result = route_file(cfg, src, parsed)
    assert not result.quarantined
    assert result.real_path == cfg.dest_non_vr / name
    assert result.real_path.is_file()
    assert not src.exists()


def test_route_vr_single(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    name = "Jane.Doe.VirtualReal.Scene.Title.4k.VR.mp4"
    src = cfg.hot_folder / name
    src.write_bytes(b"vr")
    result = route_file(cfg, src, parse_filename(name))
    expected = tmp_path / "VR" / "Jane.Doe" / name
    assert result.real_path == expected
    assert expected.is_file()
    assert result.symlink_paths == ()


def test_route_vr_multi_actor_symlinks(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    name = "Jane.Doe.And.John.Smith.And.Alex.Lee.Studio.Name.Title.4k.VR.mp4"
    src = cfg.hot_folder / name
    src.write_bytes(b"multi")
    result = route_file(cfg, src, parse_filename(name))
    real = tmp_path / "VR" / "Jane.Doe" / name
    assert result.real_path == real
    assert real.is_file()
    assert len(result.symlink_paths) == 2
    for actor in ("John.Smith", "Alex.Lee"):
        link = tmp_path / "VR" / actor / name
        assert link.is_symlink()
        assert link.resolve() == real.resolve()


def test_quarantine_bad_name(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    repo = SqliteInventoryRepository(cfg.inventory_db)
    bad = cfg.hot_folder / "garbage file.mp4"
    bad.write_bytes(b"x")
    rec = process_file(cfg, bad, repo, wait_stable=True)
    assert rec is None
    assert not bad.exists()
    assert any(cfg.quarantine_folder.iterdir())
    repo.close()


def test_scan_upserts_inventory(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    repo = SqliteInventoryRepository(cfg.inventory_db)
    name = "Jane.Doe.Bang.Scene.Title.4k.mp4"
    (cfg.hot_folder / name).write_bytes(b"data")
    records = scan_hot_folder(cfg, repo)
    assert len(records) == 1
    assert records[0].full_path.endswith(name)
    assert repo.get_by_path(records[0].full_path) is not None
    repo.close()


def test_collision_leave_in_hot(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    name = "Jane.Doe.Bang.Scene.Title.4k.mp4"
    dest = cfg.dest_non_vr / name
    dest.write_bytes(b"existing")
    src = cfg.hot_folder / name
    src.write_bytes(b"new")
    result = route_file(cfg, src, parse_filename(name))
    assert result.skipped
    assert src.exists()
    assert dest.read_bytes() == b"existing"
