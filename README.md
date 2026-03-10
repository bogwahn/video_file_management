# video-file-management

A clean, object-oriented Python library for video file management: metadata models, chapter/bookmark handling, and utility helpers.

## Structure

```
src/
  video_file_management/
    __init__.py            # package initialization (to be added as you build)
    domain/                # core domain models (e.g., VideoFile, VideoMetadata)
    marks/                 # chapters, bookmarks, protocols
    utils/                 # parsing, timecode utilities, I/O helpers

tests/                     # add tests as features are implemented
quickactions/              # Finder Quick Action wrappers (bash)
pyproject.toml             # build + tooling configuration
```

## Get started

- Create your core classes under `src/video_file_management/domain/` and feature modules under `marks/` and `utils/`.
- Add `__init__.py` files to each package as you implement modules.
- Optional: install locally in editable mode during development:

```bash
pip install -e .
```

## Commands

- `remux2mp4`: lossless remux into MP4 (ffmpeg stream copy).
  - Installed via `pip install -e .` (console script).
  - Local wrapper: `scripts/remux2mp4`.
- `watchForBookmarks`: watch bookmarks directory, generate chapters, and embed them.
  - Installed via `pip install -e .` (console script).

## Design notes

- Favor small, cohesive classes with clear responsibilities.
- Use protocols/ABCs to define extensible interfaces for marks (chapters/bookmarks) and storage backends.
- Keep parsing/formatting logic in `utils/`; keep domain models pure and framework-agnostic.

## Roadmap (suggested)

- `domain.VideoFile` and `domain.VideoMetadata`
- `marks.ChaptersFile` and `marks.BookmarksFile` with read/write strategies
- `utils.timecode` helpers and path/IO utilities
- CLI wrappers and import/export adapters (MKV, MP4, CSV/JSON)

## macOS helpers

- Finder Quick Action (context menu + hotkey) to **remux compatible files to MP4 without re-encoding**:
  - `macos/RemuxToMP4-QuickAction.md`
  - Quick Action wrapper: `quickactions/remux-to-mp4.sh`
