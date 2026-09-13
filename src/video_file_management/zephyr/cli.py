"""CLI entrypoint for the Zephyr FileWatcher daemon."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from video_file_management.zephyr.config import load_config
from video_file_management.zephyr.inventory.sqlite import SqliteInventoryRepository
from video_file_management.zephyr.watcher.daemon import ensure_hot_folder, run_watcher, scan_hot_folder


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="zephyr-watcher",
        description="Zephyr download-core FileWatcher: ensure hot_folder, route VR/Non-VR, upsert inventory.",
    )
    p.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config/zephyr.sample.yaml"),
        help="Path to Zephyr YAML config (default: config/zephyr.sample.yaml)",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Process current hot_folder contents once and exit (no continuous watch).",
    )
    p.add_argument(
        "--ensure-hot-only",
        action="store_true",
        help="Only create hot_folder if missing, then exit.",
    )
    p.add_argument(
        "--log-level",
        default=None,
        help="Override config log_level (DEBUG, INFO, …)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    level = args.log_level or cfg.log_level
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.ensure_hot_only:
        path = ensure_hot_folder(cfg)
        print(f"hot_folder ready: {path}")
        return 0

    repo = SqliteInventoryRepository(cfg.inventory_db)
    try:
        if args.once:
            records = scan_hot_folder(cfg, repo)
            print(f"processed {len(records)} file(s)")
            for r in records:
                print(f"  {r.full_path}")
            return 0
        run_watcher(cfg, repo)
        return 0
    finally:
        repo.close()


if __name__ == "__main__":
    sys.exit(main())
