# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository overview

- Language/runtime: Python (>= 3.10), src-layout package at `src/video_file_management`.
- Purpose: Two minimal, stackable CLI commands—`chapterize` (chapter CRUD) and `remux` (lossless MP4 conversion).
- External tools required at runtime: `ffmpeg`, `MP4Box` (GPAC).
- External tools optional: `xattr` (for extended-attribute chapter storage on macOS).
- Tooling configured in `pyproject.toml`: `pytest`, `black`, `isort`, `mypy`, `coverage`.

## Setup

- Install the package in editable mode (and commonly used dev tools):

```bash
python -m pip install -e .
python -m pip install -U pytest black isort mypy build coverage
```

## Common commands

- Lint (check only):

```bash
black . --check
isort . --check-only
```

- Auto-format:

```bash
black . && isort .
```

- Type-check:

```bash
mypy src
```

- Run tests (pytest configured via `pyproject.toml` to look in `tests/`):

```bash
pytest -q
```

- Run a single test:

```bash
# by node::test selection
pytest tests/test_timecode.py::test_parse_timecode

# or by keyword expression
pytest -q -k "timecode and not slow"
```

- Test coverage:

```bash
coverage run -m pytest
coverage report -m
# optional HTML report
coverage html
```

- Build distribution (sdist + wheel):

```bash
python -m build
# install a built wheel
python -m pip install dist/*.whl
```

## High-level architecture

### Packages

- **`chapterize/`** — Chapter CRUD (add, list, edit, remove)
  - `cli.py` — Argparse entry point; orchestrates discovery, merging, conflict resolution, writing.
  - Service modules (discovery, merging, metadata reading) — Business logic abstracted from CLI.
- **`remux/`** — Lossless MP4 conversion
  - `cli.py` — Argparse entry point; validates codecs, invokes ffmpeg.
  - `service.py` — Remux orchestration; codec policy validation.
  - `remux_quickaction.py` — Thin wrapper for macOS Quick Action integration.
- **`marks/`** — Shared chapter/mark infrastructure
  - `models.py` — `VideoMark`: timecode + label (frozen, hashable).
  - `readers.py` — Parse chapters/bookmarks from text files into `VideoMarksFile`.
  - `writers.py` — Write chapters to MP4 (via MP4Box), extended attributes, or ffmpeg metadata tracks.
- **`utils/`** — Shared utilities
  - `timecode.py` — Parse/format `HH:MM:SS.mmm` strings as `timedelta`.
  - Path and I/O helpers.

### Serialization formats

- **Human-readable:** `[HH:MM:SS.mmm] Label` per line (chapters text file).
- **Nero/MP4Box format** (for MP4 chapter embedding):

  ```text
  CHAPTER01=HH:MM:SS.mmm
  CHAPTER01NAME=Title
  ```

- **FFmpeg metadata track:** Chapters embedded as FLAC metadata blocks in MP4 (no auto-extension).

### Error handling philosophy

- Non-throwing readers/writers preferred: return empty/partial results rather than raise. Callers decide if partial is acceptable.
- CLI catches exceptions and returns non-zero exit code with error message.
- Tests use synthetic, ephemeral data (no real video files); cleanup guaranteed via context managers or temp file scope.
