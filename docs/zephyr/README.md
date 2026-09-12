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
| `src/video_file_management/zephyr/parser.py` | Filename grammar parse/build (compact studio; optional resolution) |
| `src/video_file_management/zephyr/enrich.py` | Post-move resolution probe via `metadata_reader` / ffprobe |
| `src/video_file_management/zephyr/inventory/` | `InventoryRepository` + SQLite |
| `src/video_file_management/zephyr/watcher/` | Route VR/Non-VR, symlinks, daemon; calls enrich after move |
| `src/video_file_management/zephyr/cli.py` | `zephyr-watcher` entrypoint |
| `userscripts/zephyr-title-normalizer.user.js` | TamperMonkey `<title>` rewrite (NS host selectors) |
| `docs/zephyr/download-helper.md` | Point DH at hot folder |
| `docs/zephyr/newsensations.md` | Install + verify notes for newsensations.com |

## Naming (locked 2026-09-12)

- **Studio:** compact token — no whitespace, no internal dots. `"New Sensations"` → `NewSensations` (appears as `.NewSensations.` between actor and title blocks).
- **Resolution:** if unknown at download/title time, **omit** the token (do not default to `.4k.`).
- **Enrichment:** after FileWatcher moves a conforming file, if resolution is missing it calls `zephyr.enrich.apply_resolution_enrichment`, which uses existing `video_file_management.metadata_reader.read_file_metadata` (ffprobe) to map width/height → `480p|540p|720p|1080p|2k|4k` and renames when a token is resolved.

## Tests

```bash
pytest tests/zephyr -q
```
