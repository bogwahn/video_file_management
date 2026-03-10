#!/bin/bash
# Fix mChapters loading issues by clearing problematic bookmarks

set -e

echo "🔧 mChapters Fix Script"
echo "======================"
echo ""

# Check if mChapters is running
if pgrep -f "mChapters" > /dev/null; then
    echo "⚠️  mChapters is currently running."
    echo "   Quitting mChapters..."
    killall mChapters 2>/dev/null || true
    sleep 2
    
    # Force quit if still running
    if pgrep -f "mChapters" > /dev/null; then
        echo "   Force quitting..."
        killall -9 mChapters 2>/dev/null || true
        sleep 1
    fi
fi

echo "✅ mChapters is not running"
echo ""

# Backup preferences
PREF_DIR="$HOME/Library/Containers/jp.tranquillitybase.mChapters"
PREF_FILE="$PREF_DIR/Data/Library/Preferences/jp.tranquillitybase.mChapters.plist"

if [ -f "$PREF_FILE" ]; then
    BACKUP_FILE="${PREF_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📦 Backing up preferences..."
    cp "$PREF_FILE" "$BACKUP_FILE"
    echo "   Backup saved to: $BACKUP_FILE"
    echo ""
fi

# Backup + clear LaunchServices “Recent Documents” list for mChapters
# (stale recent-document bookmarks can break file open/restore on startup)
RECENTS_DIR="$HOME/Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments"
RECENTS_FILE="$RECENTS_DIR/jp.tranquillitybase.mchapters.sfl4"
if [ -f "$RECENTS_FILE" ]; then
    RECENTS_BACKUP="${RECENTS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "🧾 Backing up recent documents list..."
    cp "$RECENTS_FILE" "$RECENTS_BACKUP"
    echo "   Backup saved to: $RECENTS_BACKUP"
    echo "🧹 Clearing recent documents list for mChapters..."
    rm -f "$RECENTS_FILE"
    echo ""
fi

# Option 1: Remove just the MCDocStatus key (keeps other preferences)
echo "🔍 Removing problematic MCDocStatus bookmarks..."
defaults delete jp.tranquillitybase.mChapters MCDocStatus 2>/dev/null || echo "   (MCDocStatus key not found or already removed)"

# Option 2: If that doesn't work, we can remove the entire preferences file
# Uncomment the next lines if Option 1 doesn't work:
# echo "🗑️  Removing preferences file..."
# rm -f "$PREF_FILE"

# Also clear any cached bookmarks
echo "🧹 Clearing cached bookmarks..."
find "$PREF_DIR" -name "*bookmark*" -type f -delete 2>/dev/null || true

echo ""
echo "✅ Fix complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Launch mChapters: open -a mChapters"
echo "   2. Try opening a local video file"
echo "   3. If it still hangs, run this script again and uncomment the 'remove preferences file' section"
echo ""

