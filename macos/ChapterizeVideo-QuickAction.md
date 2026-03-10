## macOS Finder Quick Action: Chapterize Video

This creates a **Finder context menu** item (Quick Action / Service) that allows you to right-click a bookmarks text file and instantly embed those bookmarks as chapters into the corresponding video file.

### Prerequisites

- **ffmpeg available on PATH**
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
cp "quickactions/chapterize-video.sh" "$HOME/bin/chapterize-video"
chmod +x "$HOME/bin/chapterize-video"
```

Verify:

```bash
"$HOME/bin/chapterize-video" --help
```

### 2) Create the Finder Quick Action (Automator)

1. Open **Automator**
2. Create a new document: **Quick Action**
3. At the top:
   - “Workflow receives current” = **documents** or **files or folders**
   - “in” = **Finder**
4. Add action: **Run Shell Script**
5. Configure:
   - Shell: `/bin/zsh` (or `/bin/bash`)
   - “Pass input”: **as arguments**
6. Paste this script (edit the path if you chose a different install location):

```bash
"$HOME/bin/chapterize-video" "$@"
```

7. Save the Quick Action as: **Chapterize Video**

Now, in Finder: right-click a bookmarks file → **Quick Actions** (or **Services**) → “Chapterize Video”.

### Logs / troubleshooting

- The script writes a log at: `~/Library/Logs/video_file_management/chapterize-video.log`
- If an error occurs, an AppleScript dialog box will appear.
