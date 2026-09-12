# Video DownloadHelper — Zephyr spike operator notes

Zephyr does **not** build or ship Video DownloadHelper. The spike only requires the operator to point DH at the locked hot folder so TamperMonkey’s rewritten `<title>` becomes the download filename.

## Hot folder (locked)

| Role | Path |
|------|------|
| Hot folder (inbox) | `/Internal/Zetc/Download` |
| Path rule | Internal dock SSD — **no** `/Volumes` prefix |

FileWatcher creates this directory on startup if missing. TamperMonkey **cannot** `mkdir` on the host filesystem.

## Operator checklist

1. Install / open **Video DownloadHelper** (browser extension).
2. Set its download directory to **`/Internal/Zetc/Download`** (same as `hot_folder` in `config/zephyr.sample.yaml`).
3. Prefer settings that use the **page title** as the suggested filename (do not let DH invent a different name).
4. Install `userscripts/zephyr-title-normalizer.user.js` (v0.3.0+) in TamperMonkey; confirm `<title>` uses compact studio (`NewSensations`) and omits resolution when unknown.
5. Run `zephyr-watcher` so files are routed out of the hot folder after download completes (missing resolution may be enriched via ffprobe after move).

## Temp / partial names

Watcher ignores common incomplete suffixes (`.part`, `.crdownload`, `.tmp`, `.download`, `.partial`) and waits until file size is stable before parsing.

## Out of scope

- Building DownloadHelper itself
- Browser-native save-dialog plugins
- Zephyr file-manager UI / custom Finder icons
