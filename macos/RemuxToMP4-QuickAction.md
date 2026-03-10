## macOS Finder Quick Action: Remux to MP4 (no re-encode)

This creates a **Finder context menu** item (Quick Action / Service) that remuxes compatible video files into an **MP4 container** using **ffmpeg stream copy** (`-c copy`). If the file contains streams that are not MP4-compatible, it **refuses** (no re-encoding).

### What “compatible” means (this tool’s rules)

- **Video codecs allowed**: `h264`, `hevc`, `mpeg4`
- **Audio codecs allowed**: `aac`, `alac`, `mp3`
- **Subtitle streams**: ignored/dropped
- **Other stream types** (`attachment`, `data`, etc.): ignored/dropped

If you want to expand the allow-list, edit:

- `src/video_file_management/remux/remux_quickaction.py`

### Prerequisites

- **ffmpeg + ffprobe available on PATH**
- **Python package installed** (so the Quick Action wrapper can import it)

If you use Homebrew (recommended):

```bash
brew install ffmpeg
```

Install the package from the repo (editable install):

```bash
pip install -e .
```

### 1) Put the Quick Action wrapper somewhere stable and make it executable

Pick a location that won’t move (example uses `~/bin`):

```bash
mkdir -p "$HOME/bin"
cp "quickactions/remux-to-mp4.sh" "$HOME/bin/remux-to-mp4"
chmod +x "$HOME/bin/remux-to-mp4"
```

Verify:

```bash
"$HOME/bin/remux-to-mp4" --help
```

### 2) Create the Finder Quick Action (Automator)

1. Open **Automator**
2. Create a new document: **Quick Action**
3. At the top:
   - “Workflow receives current” = **movie files**
   - “in” = **Finder**
4. Add action: **Run Shell Script**
5. Configure:
   - Shell: `/bin/zsh` (or `/bin/bash`)
   - “Pass input”: **as arguments**
6. Paste this script (edit the path if you chose a different install location):

```bash
"$HOME/bin/remux-to-mp4" "$@"
```

7. Save the Quick Action as: **Remux to MP4 (Copy)**

Now, in Finder: right-click a file → **Quick Actions** (or **Services**) → “Remux to MP4 (Copy)”.

### 3) Assign a keyboard shortcut (hotkey)

macOS Ventura/Sonoma/Sequoia:

1. **System Settings** → **Keyboard** → **Keyboard Shortcuts…**
2. Find **Services** (or **Quick Actions** / **Files and Folders** depending on OS)
3. Locate **Remux to MP4 (Copy)**
4. Add a shortcut (example: `⌥⌘M`)

### Output behavior

- Output is written next to the source file as `<stem>.mp4`.
- If `<stem>.mp4` already exists, it skips the file.
- If the input is already `.mp4`, it skips it.

### Logs / troubleshooting

- The script writes a log at: `~/Library/Logs/video_file_management/remux-to-mp4.log`
- If a file is rejected, the reason is logged and a macOS notification is shown.

