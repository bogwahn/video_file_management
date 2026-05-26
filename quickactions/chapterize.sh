#!/bin/bash

# macOS Finder Quick Action Wrapper: Chapterize Video
# This script invokes the Python CLI to chapterize a video based on a bookmarks file.

# Use a deterministic PATH for Finder/Automator-launched shells.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${REPO_DIR}/.venv/bin/python"

if [ -x "${VENV_PYTHON}" ]; then
    PYTHON_BIN="${VENV_PYTHON}"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    PYTHON_BIN="python3"
fi

export PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"

LOG_DIR="$HOME/Library/Logs/video_file_management"
LOG_FILE="$LOG_DIR/chapterize-video.log"
mkdir -p "$LOG_DIR"

echo "=== Chapterize Video Action Triggered: $(date) ===" >> "$LOG_FILE"
echo "Input arguments: $*" >> "$LOG_FILE"

"${PYTHON_BIN}" -m video_file_management.chapterize.cli "$@" >> "$LOG_FILE" 2>&1
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "Success." >> "$LOG_FILE"
else
    echo "Failed with exit code: $RESULT" >> "$LOG_FILE"
fi

exit $RESULT
