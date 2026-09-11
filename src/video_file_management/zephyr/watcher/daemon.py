"""FileWatcher daemon: ensure hot_folder, watch, parse, route, inventory upsert."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from video_file_management.zephyr.config import ZephyrConfig, assert_no_hot_dest_loop
from video_file_management.zephyr.inventory.models import InventoryRecord
from video_file_management.zephyr.inventory.repository import InventoryRepository
from video_file_management.zephyr.parser import ParseError, parse_filename
from video_file_management.zephyr.watcher.router import is_partial_or_ignored, quarantine_file, route_file
from video_file_management.zephyr.watcher.sidecar import load_sidecar

log = logging.getLogger(__name__)


def ensure_hot_folder(cfg: ZephyrConfig) -> Path:
    """Create hot_folder (and parents) if missing. Fail loudly if Internal root missing when expected."""
    hot = cfg.hot_folder
    # If path is under /Internal, the mount tip must exist (or we create full tree in tests).
    internal_root = Path("/Internal")
    if str(hot).startswith("/Internal") and not internal_root.exists():
        # On Bud's Mac Mini, /Internal must be mounted. In tests we use temp paths.
        # Only raise when the configured path literally uses /Internal and it is absent.
        raise FileNotFoundError(
            "Internal dock SSD path /Internal is not available; "
            "cannot create or watch hot_folder. Mount Internal or fix config."
        )
    hot.mkdir(parents=True, exist_ok=True)
    return hot


def wait_until_stable(path: Path, stable_seconds: float, *, poll: float | None = None) -> bool:
    """Return True when size is unchanged for stable_seconds; False if file disappears."""
    if not path.is_file():
        return False
    if stable_seconds <= 0:
        return True
    poll_s = poll if poll is not None else min(0.5, max(0.05, stable_seconds / 3))
    last_size = -1
    stable_for = 0.0
    while stable_for < stable_seconds:
        if not path.is_file():
            return False
        size = path.stat().st_size
        if size == last_size and size >= 0:
            stable_for += poll_s
        else:
            last_size = size
            stable_for = 0.0
        time.sleep(poll_s)
    return path.is_file()


def process_file(
    cfg: ZephyrConfig,
    path: Path,
    repo: InventoryRepository,
    *,
    wait_stable: bool = True,
) -> InventoryRecord | None:
    """Parse one hot-folder file, route it, upsert inventory. Returns record or None if skipped."""
    if is_partial_or_ignored(path):
        return None
    if not path.is_file():
        return None

    # Never process files already outside hot (safety).
    try:
        if path.resolve().parent != cfg.hot_folder.resolve():
            # Allow nested only if same hot root; spike watches non-recursive one level.
            if cfg.hot_folder.resolve() not in path.resolve().parents and path.resolve().parent != cfg.hot_folder.resolve():
                log.debug("Ignoring file outside hot_folder: %s", path)
                return None
    except OSError:
        pass

    if wait_stable and not wait_until_stable(path, cfg.stable_seconds):
        log.info("File vanished before stable: %s", path)
        return None

    sidecar = None if cfg.sidecar == "never" else load_sidecar(path)
    if cfg.sidecar == "required" and sidecar is None:
        quarantine_file(cfg, path, "sidecar required but missing")
        return None

    try:
        parsed = parse_filename(path.name)
    except ParseError as exc:
        quarantine_file(cfg, path, f"bad name: {exc}")
        return None

    source_url = None
    metadata: dict = {"is_vr": parsed.is_vr, "actors": list(parsed.actors), "studio": parsed.studio}
    if sidecar:
        source_url = sidecar.get("source_url") or sidecar.get("url")
        metadata["sidecar"] = {k: sidecar[k] for k in sidecar if k not in {"source_url", "url"}}
        if "is_vr" in sidecar:
            metadata["sidecar_is_vr"] = sidecar["is_vr"]

    result = route_file(cfg, path, parsed)
    if result.skipped:
        log.warning("Skipped %s (%s)", path.name, result.reason)
        return None
    if result.quarantined:
        return None

    record = InventoryRecord(
        full_path=str(result.real_path.resolve()),
        filename=result.real_path.name,
        source_url=source_url,
        metadata=metadata,
    )
    if result.symlink_paths:
        record.metadata["secondary_links"] = [str(p) for p in result.symlink_paths]

    return repo.upsert(record)


def scan_hot_folder(cfg: ZephyrConfig, repo: InventoryRepository) -> list[InventoryRecord]:
    """One-shot process of current files in hot_folder (non-recursive)."""
    ensure_hot_folder(cfg)
    assert_no_hot_dest_loop(cfg)
    records: list[InventoryRecord] = []
    for entry in sorted(cfg.hot_folder.iterdir()):
        if not entry.is_file():
            continue
        rec = process_file(cfg, entry, repo, wait_stable=True)
        if rec:
            records.append(rec)
    return records


def run_watcher(
    cfg: ZephyrConfig,
    repo: InventoryRepository,
    *,
    stop_when: Callable[[], bool] | None = None,
    poll_interval: float = 1.0,
) -> None:
    """Polling watcher (works without watchdog event loops for tests/spike).

    Also registers a watchdog observer when the package is available for lower latency.
    """
    ensure_hot_folder(cfg)
    assert_no_hot_dest_loop(cfg)
    cfg.quarantine_folder.mkdir(parents=True, exist_ok=True)
    log.info("Watching hot_folder=%s", cfg.hot_folder)

    observer = None
    pending: set[Path] = set()

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class Handler(FileSystemEventHandler):
            def on_created(self, event):  # type: ignore[no-untyped-def]
                if not event.is_directory:
                    pending.add(Path(event.src_path))

            def on_modified(self, event):  # type: ignore[no-untyped-def]
                if not event.is_directory:
                    pending.add(Path(event.src_path))

            def on_moved(self, event):  # type: ignore[no-untyped-def]
                if not event.is_directory:
                    pending.add(Path(event.dest_path))

        observer = Observer()
        observer.schedule(Handler(), str(cfg.hot_folder), recursive=False)
        observer.start()
        log.info("watchdog observer started")
    except ImportError:
        log.warning("watchdog not installed; using poll-only mode")

    try:
        while True:
            if stop_when and stop_when():
                break
            # Seed from directory listing so we catch files present at start / poll-only.
            try:
                for entry in cfg.hot_folder.iterdir():
                    if entry.is_file() and not is_partial_or_ignored(entry):
                        pending.add(entry)
            except OSError as exc:
                log.error("hot_folder listing failed: %s", exc)
                raise

            batch = list(pending)
            pending.clear()
            for path in batch:
                try:
                    process_file(cfg, path, repo, wait_stable=True)
                except Exception:  # noqa: BLE001 — keep daemon alive
                    log.exception("Failed processing %s", path)

            time.sleep(poll_interval)
    finally:
        if observer is not None:
            observer.stop()
            observer.join(timeout=5)
