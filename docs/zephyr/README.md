# Zephyr download-core spike

Spike: TamperMonkey title normalizer + Video DownloadHelper (operator-configured) + FileWatcher + SQLite inventory.

**Plan (source of truth):** project store `docs/zephyr-core-spike.md` (not duplicated here).

## Quick start

```bash
pip install -e ".[zephyr]"
# or: pip install -e .   # pulls PyYAML + watchdog as package deps once added

# Ensure hot folder (on Bud's Mac Mini when /Internal is mounted):
zephyr-watcher -c config/zephyr.sample.yaml --ensure-hot-only

# One-shot process files already in hot_folder:
zephyr-watcher -c /path/to/zephyr.yaml --once

# Continuous watch:
zephyr-watcher -c /path/to/zephyr.yaml
```

Copy `config/zephyr.sample.yaml` and override paths for local/dev (use temp dirs; do not point hot at a dest).

## Components

| Path | Role |
|------|------|
| `config/zephyr.sample.yaml` | `hot_folder`, `dest.vr`, `dest.non_vr`, quarantine, collision, sidecar defaults |
| `src/video_file_management/zephyr/parser.py` | Filename grammar parse/build |
| `src/video_file_management/zephyr/inventory/` | `InventoryRepository` + SQLite |
| `src/video_file_management/zephyr/watcher/` | Route VR/Non-VR, symlinks, daemon |
| `src/video_file_management/zephyr/cli.py` | `zephyr-watcher` entrypoint |
| `userscripts/zephyr-title-normalizer.user.js` | TamperMonkey `<title>` rewrite |
| `docs/zephyr/download-helper.md` | Point DH at hot folder |

## Tests

```bash
pytest tests/zephyr -q
```
