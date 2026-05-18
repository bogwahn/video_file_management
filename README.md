# video-file-management

Minimal, stackable video utility commands: **chapterize** (chapter CRUD) and **remux** (lossless MP4 conversion). Installed globally via pipx.

## Quick start

### Installation

```bash
pipx install -e /path/to/video_file_management
```

Commands are then available globally:

```bash
chapterize --help
remux --help
```

### Commands

- **`chapterize`**: Add, edit, list, remove chapters in video files.
  - Read chapters from text file, write to MP4 (via MP4Box), xattr, or ffmpeg metadata tracks.
- **`remux`**: Lossless remux into MP4 container (ffmpeg stream copy, no re-encode).

Both commands are stackable: process multiple files, integrate into workflows.

## Structure

```
src/video_file_management/
  chapterize/             # Chapter CRUD: read/write chapters, handle formats
    cli.py                # Entry point (argparse)
    [service modules]     # Discovery, metadata I/O, writer backend selection
  marks/                  # Shared chapter/mark models, readers, writers
    models.py             # VideoMark, timecode formatting
    readers.py, writers.py
  remux/                  # MP4 remux (stream copy)
    cli.py                # Entry point (argparse)
    service.py            # ffmpeg invocation, file validation
    remux_quickaction.py   # macOS Quick Action integration
  [shared utilities]      # Timecode parsing, path helpers
```

## Development

Install in editable mode:

```bash
pip install -e .
```

Run tests:

```bash
pytest
```

Format & lint:

```bash
black . && isort .
mypy src
```

## Design philosophy

- **Two commands, stable scope.** No roadmap for new features; changes are refactors or bug fixes within chapterize/remux.
- **Plugin architecture (future).** When remux gains variants (MP4→MKV, MP4→WebM, etc.), refactor into plugin system; don't expand scope now.
- **No in-repo fallbacks.** pipx-installed commands are the standard. Direct `python -m video_file_management.X.cli` works if needed but isn't documented.

## macOS Quick Actions

Finder context menu shortcuts (installed via Automator):
- **Chapterize**: `quickactions/chapterize.sh`
- **Remux**: `quickactions/remux.sh`

To set up: Record in Automator → pass file path to the corresponding `.sh` script.
