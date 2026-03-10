# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository overview
- Language/runtime: Python (>= 3.10), src-layout package at `src/video_file_management`.
- Purpose: OO library for video file management (marks/chapters, timecode utilities, readers/writers).
- External tools used at runtime (optional): `ffmpeg`, `MP4Box` (GPAC), `xattr` (Python module or macOS CLI).
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
- `utils/timecode.py`
  - `parse_timecode(str) -> timedelta`: parses `HH:MM:SS.mmm` strings.
  - `format_timecode(timedelta) -> str`: formats to `HH:MM:SS.mmm`.
- `marks/models.py`
  - `VideoMark` dataclass: immutable (frozen, slots) pair of `timecode: timedelta` and `label: str`.
- `marks/protocols.py`
  - `VideoMarksFile` protocol: minimal interface for mark collections (`add`, `remove`, `marks`, `to_string`, `file_path`).
- `marks/chapters_file.py`
  - `ChaptersFile`: concrete `VideoMarksFile` storing unique `VideoMark`s; serializes as `[HH:MM:SS.mmm] Label` per line.
- `marks/readers.py`
  - `ChaptersFileReader`: parses a chapters text file into `ChaptersFile`; ignores malformed lines, non-throwing if file absent.
- `marks/writers.py`
  - `ChapterMetadataWriter`: writes serialized chapters to extended attributes (`com.video_file_management.chapters`) via Python `xattr` or macOS `xattr` CLI fallback.
  - `MP4ChaptersWriter`: removes existing chapters with `ffmpeg`, generates Nero-format chapter text, imports with `MP4Box -chap`, atomically replaces original file.
- `marks/ffmpeg_writer.py`
  - `ChapterTrackWriter`: alternative writer that uses `MP4Box` to create a new MP4 with chapters (Nero format) without auto-extension; performs atomic replace with backup.

### Serialization formats
- Human-readable chapters file: `[HH:MM:SS.mmm] Label` per line (read/write via `ChaptersFile` + `ChaptersFileReader`).
- Nero/MP4Box chapters text (used by MP4 writers):
  - `CHAPTER01=HH:MM:SS.mmm`
  - `CHAPTER01NAME=Title`

### Error handling philosophy
- Readers/writers prefer non-throwing behavior: return early if prerequisites are missing (file not found, tools unavailable) and swallow exceptions for robustness.
