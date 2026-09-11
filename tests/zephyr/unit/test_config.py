"""Config loading tests."""

from pathlib import Path

import pytest

from video_file_management.zephyr.config import assert_no_hot_dest_loop, load_config


def test_sample_config_loads() -> None:
    root = Path(__file__).resolve().parents[3]
    cfg = load_config(root / "config" / "zephyr.sample.yaml")
    assert str(cfg.hot_folder) == "/Internal/Zetc/Download"
    assert "{First.Actress}" in cfg.dest_vr_template
    assert str(cfg.dest_non_vr) == "/Volumes/ZetcOld/Uncategorized"
    assert cfg.vr_secondary_link == "symlink"
    assert cfg.resolve_vr_dest("Jane.Doe") == Path("/Volumes/Zetc/VR/Jane.Doe")


def test_hot_dest_loop_detected(tmp_path: Path) -> None:
    shared = tmp_path / "same"
    shared.mkdir()
    cfg = load_config(
        data={
            "hot_folder": str(shared),
            "dest": {"vr": str(tmp_path / "VR" / "{First.Actress}"), "non_vr": str(shared)},
            "quarantine_folder": str(tmp_path / "q"),
            "inventory_db": str(tmp_path / "db.sqlite3"),
        }
    )
    with pytest.raises(ValueError, match="hot_folder must not equal"):
        assert_no_hot_dest_loop(cfg)
