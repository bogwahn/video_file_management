"""Config loading tests."""

from pathlib import Path

import pytest

from video_file_management.zephyr.config import assert_no_hot_dest_loop, load_config


def test_sample_config_loads() -> None:
    root = Path(__file__).resolve().parents[3]
    cfg = load_config(root / "config" / "zephyr.sample.yaml")
    assert str(cfg.hot_folder) == "/Internal/Zetc/Download"
    assert "{First.Actress}" in cfg.dest_folder_vr_template
    assert "{Studio}" in cfg.dest_folder_non_vr_template
    assert cfg.dest_folder_non_vr_template == "/Volumes/ZetcOld/Studios/{Studio}"
    assert cfg.vr_secondary_link == "symlink"
    assert cfg.resolve_vr_dest("Jane.Doe") == Path("/Volumes/Zetc/VR/Jane.Doe")
    assert cfg.resolve_non_vr_dest("NewSensations") == Path(
        "/Volumes/ZetcOld/Studios/NewSensations"
    )


def test_hot_dest_loop_detected(tmp_path: Path) -> None:
    shared = tmp_path / "same"
    shared.mkdir()
    cfg = load_config(
        data={
            "hot_folder": str(shared),
            "dest_folder": {
                "vr": str(tmp_path / "VR" / "{First.Actress}"),
                "non_vr": str(shared),
            },
            "quarantine_folder": str(tmp_path / "q"),
            "inventory_db": str(tmp_path / "db.sqlite3"),
        }
    )
    with pytest.raises(ValueError, match="hot_folder must not equal"):
        assert_no_hot_dest_loop(cfg)


def test_legacy_dest_key_still_loads(tmp_path: Path) -> None:
    """Older configs using dest: still work; dest_folder is preferred when both present."""
    studios = tmp_path / "Studios" / "{Studio}"
    cfg = load_config(
        data={
            "hot_folder": str(tmp_path / "hot"),
            "dest": {
                "vr": str(tmp_path / "VR" / "{First.Actress}"),
                "non_vr": str(studios),
            },
            "quarantine_folder": str(tmp_path / "q"),
            "inventory_db": str(tmp_path / "db.sqlite3"),
        }
    )
    assert cfg.dest_folder_non_vr_template == str(studios)
    assert cfg.resolve_non_vr_dest("Bang") == tmp_path / "Studios" / "Bang"
