"""Route parsed downloads to configured VR / Non-VR destinations."""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from video_file_management.zephyr.config import ZephyrConfig
from video_file_management.zephyr.parser import ParsedFilename

log = logging.getLogger(__name__)

PARTIAL_SUFFIXES = (
    ".part",
    ".crdownload",
    ".tmp",
    ".download",
    ".partial",
    ".zephyr.json",
)


@dataclass(frozen=True)
class RouteResult:
    real_path: Path
    symlink_paths: tuple[Path, ...]
    quarantined: bool
    skipped: bool
    reason: str = ""


def is_partial_or_ignored(path: Path) -> bool:
    name = path.name
    lower = name.lower()
    if name.startswith("."):
        return True
    if lower.endswith(PARTIAL_SUFFIXES):
        return True
    if lower.endswith(".zephyr.json"):
        return True
    return False


def cross_volume_move(src: Path, dest: Path) -> Path:
    """Move file; use copy+verify+delete when rename fails (cross-volume)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        src.rename(dest)
        return dest
    except OSError:
        shutil.copy2(src, dest)
        if dest.stat().st_size != src.stat().st_size:
            dest.unlink(missing_ok=True)
            raise OSError(f"copy verify failed: {src} -> {dest}")
        src.unlink()
        return dest


def _handle_collision(cfg: ZephyrConfig, src: Path, dest: Path) -> str | None:
    """Return action taken if collision blocks move: 'skip'|'quarantine', else None."""
    if not dest.exists() and not dest.is_symlink():
        return None
    if cfg.collision_policy == "overwrite":
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        return None
    if cfg.collision_policy == "quarantine":
        return "quarantine"
    return "skip"


def quarantine_file(cfg: ZephyrConfig, src: Path, reason: str) -> Path:
    cfg.quarantine_folder.mkdir(parents=True, exist_ok=True)
    dest = cfg.quarantine_folder / src.name
    if dest.exists():
        stem, suffix = src.stem, src.suffix
        n = 1
        while dest.exists():
            dest = cfg.quarantine_folder / f"{stem}.q{n}{suffix}"
            n += 1
    log.warning("Quarantining %s: %s", src.name, reason)
    return cross_volume_move(src, dest)


def create_secondary_link(cfg: ZephyrConfig, real_path: Path, link_path: Path) -> Path:
    """Create symlink (spike default) or document alias unsupported on non-macOS."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or link_path.is_symlink():
        if link_path.is_symlink() and Path(os.path.realpath(link_path)) == Path(os.path.realpath(real_path)):
            return link_path
        if cfg.collision_policy == "overwrite":
            link_path.unlink()
        else:
            log.warning("Secondary link exists, leaving alone: %s", link_path)
            return link_path

    if cfg.vr_secondary_link == "alias":
        # Finder aliases need macOS tooling; spike falls back to symlink with warning.
        log.warning("vr_secondary_link=alias not implemented; using symlink for %s", link_path)
    link_path.symlink_to(real_path)
    return link_path


def route_file(
    cfg: ZephyrConfig,
    src: Path,
    parsed: ParsedFilename,
) -> RouteResult:
    """Move a conforming file to Non-VR or VR dest; create secondary VR symlinks."""
    filename = parsed.filename

    if parsed.is_vr:
        if not parsed.actors:
            q = quarantine_file(cfg, src, "VR file missing actors")
            return RouteResult(q, (), True, False, "VR missing actors")
        dest_dir = cfg.resolve_vr_dest(parsed.first_actress)
        dest = dest_dir / filename
        collision = _handle_collision(cfg, src, dest)
        if collision == "skip":
            return RouteResult(src, (), False, True, f"collision at {dest}")
        if collision == "quarantine":
            q = quarantine_file(cfg, src, f"collision at {dest}")
            return RouteResult(q, (), True, False, f"collision at {dest}")

        real = cross_volume_move(src, dest)
        links: list[Path] = []
        for actor in parsed.actors[1:]:
            link_dir = cfg.resolve_vr_dest(actor)
            link_path = link_dir / filename
            links.append(create_secondary_link(cfg, real, link_path))
        return RouteResult(real, tuple(links), False, False, "routed VR")

    dest = cfg.dest_non_vr / filename
    collision = _handle_collision(cfg, src, dest)
    if collision == "skip":
        return RouteResult(src, (), False, True, f"collision at {dest}")
    if collision == "quarantine":
        q = quarantine_file(cfg, src, f"collision at {dest}")
        return RouteResult(q, (), True, False, f"collision at {dest}")
    real = cross_volume_move(src, dest)
    return RouteResult(real, (), False, False, "routed Non-VR")
