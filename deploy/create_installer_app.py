import os
import stat
from pathlib import Path

def build_installer() -> None:
    """Generates the Deploy Video Tools.app in the root directory."""
    deploy_dir = Path(__file__).parent.absolute()
    output_app_path = deploy_dir / "Deploy Video Tools.app"
    
    contents_dir = output_app_path / "Contents"
    macos_dir = contents_dir / "MacOS"
    
    macos_dir.mkdir(parents=True, exist_ok=True)
    
    # Simple plist that hides the dock icon entirely
    info_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleExecutable</key>
	<string>Deploy</string>
	<key>CFBundleIdentifier</key>
	<string>com.videofilemanagement.deploy</string>
	<key>CFBundleName</key>
	<string>Deploy Video Tools</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0</string>
	<key>LSUIElement</key>
	<true/>
</dict>
</plist>"""
    (contents_dir / "Info.plist").write_text(info_plist)

    # Shell script triggering our backend deploy.py
    deploy_script = """#!/bin/zsh

LOG_FILE="$HOME/Library/Logs/video_file_management/deploy.log"
mkdir -p "$(dirname "$LOG_FILE")"
echo "=== Starting double-click deployment: $(date) ===" >> "$LOG_FILE"

# Find our location to derive project room
APP_DIR="$(dirname "$0")"
PROJECT_DIR="$(cd "$APP_DIR/../../../.." && pwd)"

# Run Deploy backend
cd "$PROJECT_DIR" || exit 1

# Note: Using python3 assumes system python, but it's universally available on macOS.
python3 deploy/deploy.py >> "$LOG_FILE" 2>&1

# Capture outcome
RESULT=$?
if [ $RESULT -eq 0 ]; then
    osascript -e 'display dialog "Installation Complete!\\n\\nThe Quick Actions (Remux to MP4, Chapterize Video) are now available in your right-click Services menu natively." buttons {"OK"} default button "OK" with title "Video File Management"'
else
    osascript -e "display dialog \\"Deployment Failed!\\n\\nCheck the log file at $LOG_FILE\\" buttons {\\"OK\\"} default button \\"OK\\" with title \\"Error\\" with icon stop"
fi
"""
    
    exec_path = macos_dir / "Deploy"
    exec_path.write_text(deploy_script)
    
    # Make the wrapper executable
    os.chmod(exec_path, exec_path.stat().st_mode | stat.S_IEXEC)
    print(f"Successfully generated macOS double-click installer at: {output_app_path}")

if __name__ == "__main__":
    build_installer()
