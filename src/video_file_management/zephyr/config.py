"""Load and validate Zephyr spike configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

DEFAULTS: dict[str, Any] = {
    "hot_folder": "/Internal/Zetc/Download",
    "dest_folder": {
        "vr": "/Volumes/Zetc/VR/{First.Actress}",
        "non_vr": "/Volumes/ZetcOld/Studios/{Studio}",
    },
    "vr_secondary_link": "symlink",
    "quarantine_folder": "/Internal/Zetc/Quarantine",
    "collision_policy": "leave_in_hot",
    "sidecar": "optional",
    "stable_seconds": 3,
    "inventory_db": "/Internal/Zetc/zephyr_inventory.sqlite3",
    "log_level": "INFO",
}


@dataclass(frozen=True)
class ZephyrConfig:
    hot_folder: Path
    dest_folder_vr_template: str
    dest_folder_non_vr_template: str
    vr_secondary_link: str
    quarantine_folder: Path
    collision_policy: str
    sidecar: str
    stable_seconds: float
    inventory_db: Path
    log_level: str

    def resolve_vr_dest(self, first_actress: str) -> Path:
        """Replace {First.Actress} (and common aliases) with the primary actor folder name."""
        folder = first_actress.strip()
        if not folder:
            raise ValueError("first_actress is required for VR destination")
        path = (
            self.dest_folder_vr_template.replace("{First.Actress}", folder)
            .replace("{first_actress}", folder)
            .replace("{actors[0]}", folder)
        )
        return Path(path)

    def resolve_non_vr_dest(self, studio: str) -> Path:
        """Replace {Studio} with the compact studio token from the filename grammar.

        Folder spelling matches the filename studio token (e.g. NewSensations),
        not spaced display form or dotted New.Sensations.
        """
        folder = studio.strip()
        if not folder:
            raise ValueError("studio is required for Non-VR destination")
        path = (
            self.dest_folder_non_vr_template.replace("{Studio}", folder)
            .replace("{studio}", folder)
        )
        return Path(path)


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _dest_folder_mapping(
    merged: Mapping[str, Any],
    *,
    overrides: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Prefer dest_folder from the latest override; accept legacy dest:; else defaults."""
    raw: Any = None
    for override in reversed(overrides):
        if "dest_folder" in override:
            raw = override["dest_folder"]
            break
        if "dest" in override:
            raw = override["dest"]
            break
    if raw is None:
        raw = merged.get("dest_folder") or DEFAULTS["dest_folder"]
    if not isinstance(raw, dict):
        raise ValueError("dest_folder must be a mapping with vr and non_vr")
    # Merge with defaults so partial overrides (e.g. only non_vr) still get vr.
    return _deep_merge(DEFAULTS["dest_folder"], raw)


def load_config(path: Path | str | None = None, *, data: Mapping[str, Any] | None = None) -> ZephyrConfig:
    """Load config from YAML path and/or explicit dict; missing keys use spike defaults."""
    merged: dict[str, Any] = dict(DEFAULTS)
    overrides: list[Mapping[str, Any]] = []
    if path is not None:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"Config root must be a mapping: {path}")
        overrides.append(raw)
        merged = _deep_merge(merged, raw)
    if data is not None:
        overrides.append(data)
        merged = _deep_merge(merged, data)

    dest = _dest_folder_mapping(merged, overrides=overrides)
    defaults_dest = DEFAULTS["dest_folder"]

    vr_link = str(merged.get("vr_secondary_link", "symlink")).lower()
    if vr_link not in {"symlink", "alias"}:
        raise ValueError("vr_secondary_link must be 'symlink' or 'alias'")

    collision = str(merged.get("collision_policy", "leave_in_hot")).lower()
    if collision not in {"leave_in_hot", "quarantine", "overwrite"}:
        raise ValueError("collision_policy must be leave_in_hot|quarantine|overwrite")

    sidecar = str(merged.get("sidecar", "optional")).lower()
    if sidecar not in {"optional", "required", "never"}:
        raise ValueError("sidecar must be optional|required|never")

    return ZephyrConfig(
        hot_folder=Path(str(merged["hot_folder"])),
        dest_folder_vr_template=str(dest.get("vr", defaults_dest["vr"])),
        dest_folder_non_vr_template=str(dest.get("non_vr", defaults_dest["non_vr"])),
        vr_secondary_link=vr_link,
        quarantine_folder=Path(str(merged["quarantine_folder"])),
        collision_policy=collision,
        sidecar=sidecar,
        stable_seconds=float(merged.get("stable_seconds", 3)),
        inventory_db=Path(str(merged["inventory_db"])),
        log_level=str(merged.get("log_level", "INFO")).upper(),
    )


def assert_no_hot_dest_loop(cfg: ZephyrConfig) -> None:
    """Fail loudly if hot_folder coincides with a destination root (no hot≡dest loops)."""
    hot = cfg.hot_folder.resolve()
    non_vr_root = Path(cfg.dest_folder_non_vr_template.split("{")[0].rstrip("/"))
    try:
        if non_vr_root.resolve() == hot:
            raise ValueError(f"hot_folder must not equal dest_folder.non_vr root: {hot}")
    except OSError:
        pass
    vr_root = Path(cfg.dest_folder_vr_template.split("{")[0].rstrip("/"))
    try:
        if vr_root.resolve() == hot:
            raise ValueError(f"hot_folder must not equal dest_folder.vr root: {hot}")
    except OSError:
        pass
