#!/bin/zsh

# macOS Finder Quick Action Wrapper: Chapterize Video
# This script invokes the Python CLI to chapterize a video based on a bookmarks file.

# Ensure we're running in a login shell environment to pick up PATH (including brew/ffmpeg)
source ~/.zprofile 2>/dev/null
source ~/.zshrc 2>/dev/null
source "$HOME/Library/Mobile Documents/com~apple~CloudDocs/development/projects/video_file_management/.venv/bin/activate" 2>/dev/null

LOG_DIR="$HOME/Library/Logs/video_file_management"
LOG_FILE="$LOG_DIR/chapterize-video.log"
mkdir -p "$LOG_DIR"

echo "=== Chapterize Video Action Triggered: $(date) ===" >> "$LOG_FILE"
echo "Input arguments: $@" >> "$LOG_FILE"

# Execute the python module directly since CLI entrypoint is installed
python3 -m video_file_management.chapterize.cli "$@" >> "$LOG_FILE" 2>&1

# Check result
RESULT=$?
if [ $RESULT -eq 0 ]; then
    echo "Success." >> "$LOG_FILE"
else
    echo "Failed with exit code: $RESULT" >> "$LOG_FILE"
    # Fallback alert if the python script died before it could show its own UI alert
    # osascript -e 'display alert "Chapterize Failed" message "Check the log file at ~/Library/Logs/video_file_management/chapterize-video.log for details." as critical'
fi

exit $RESULT
