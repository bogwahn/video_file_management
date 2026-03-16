#!/bin/bash
# Fix mChapters loading issues by clearing problematic MCDocStatus bookmarks.
# Uses PlistBuddy to bypass cfprefsd cache, which makes `defaults delete` unreliable.

echo "🔧 mChapters Fix Script"
echo "======================"
echo ""

PREF_DIR="$HOME/Library/Containers/jp.tranquillitybase.mChapters"
PREF_FILE="$PREF_DIR/Data/Library/Preferences/jp.tranquillitybase.mChapters.plist"
RECENTS_DIR="$HOME/Library/Application Support/com.apple.sharedfilelist/com.apple.LSSharedFileList.ApplicationRecentDocuments"
RECENTS_FILE="$RECENTS_DIR/jp.tranquillitybase.mchapters.sfl4"

# Step 1: Kill mChapters
if pgrep -f "mChapters" > /dev/null; then
    echo "⚠️  mChapters is currently running."
    echo "   Quitting mChapters..."
    killall mChapters 2>/dev/null || true
    sleep 2
    if pgrep -f "mChapters" > /dev/null; then
        echo "   Force quitting..."
        killall -9 mChapters 2>/dev/null || true
        sleep 1
    fi
fi
echo "✅ mChapters is not running"
echo ""

# Step 2: Kill cfprefsd so any pending writes from the dying app are discarded,
# not flushed to disk after our edits. macOS will restart cfprefsd automatically.
echo "🔄 Flushing preferences daemon (cfprefsd)..."
killall cfprefsd 2>/dev/null || true
sleep 2
echo "   Done"
echo ""

# Step 3: Backup preferences
if [ -f "$PREF_FILE" ]; then
    BACKUP_FILE="${PREF_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📦 Backing up preferences..."
    cp "$PREF_FILE" "$BACKUP_FILE"
    echo "   Backup saved to: $BACKUP_FILE"
    echo ""
fi

# Step 4: Backup + clear LaunchServices recent documents list
if [ -f "$RECENTS_FILE" ]; then
    RECENTS_BACKUP="${RECENTS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "🧾 Backing up recent documents list..."
    cp "$RECENTS_FILE" "$RECENTS_BACKUP"
    echo "   Backup saved to: $RECENTS_BACKUP"
    echo "🧹 Clearing recent documents list for mChapters..."
    rm -f "$RECENTS_FILE"
    echo ""
fi

# Step 5: Remove MCDocStatus directly via PlistBuddy, bypassing cfprefsd.
# `defaults delete` routes through cfprefsd and is subject to cache race conditions;
# PlistBuddy writes directly to the plist file on disk.
echo "🔍 Removing MCDocStatus bookmarks via PlistBuddy..."
if [ -f "$PREF_FILE" ]; then
    /usr/libexec/PlistBuddy -c "Delete :MCDocStatus" "$PREF_FILE" 2>/dev/null \
        && echo "   MCDocStatus removed" \
        || echo "   MCDocStatus key not found (already clean)"
else
    echo "   Preferences file not found — nothing to clean"
fi
echo ""

# Step 6: Clear any other cached bookmark files in the container
echo "🧹 Clearing cached bookmarks..."
find "$PREF_DIR" -name "*bookmark*" -type f -delete 2>/dev/null || true
echo ""

# Step 7: Kill cfprefsd again so it reloads cleanly from the now-patched plist
# when mChapters next launches, rather than from a stale in-memory cache.
echo "🔄 Restarting preferences daemon to load patched plist..."
killall cfprefsd 2>/dev/null || true
sleep 1
echo ""

# Step 8: Verify the key is actually gone
echo "🔎 Verifying fix..."
if [ -f "$PREF_FILE" ]; then
    if /usr/libexec/PlistBuddy -c "Print :MCDocStatus" "$PREF_FILE" > /dev/null 2>&1; then
        echo "   ⚠️  WARNING: MCDocStatus still present — try removing the full preferences file:"
        echo "       rm -f \"$PREF_FILE\""
        exit 1
    else
        echo "   ✅ MCDocStatus is gone"
    fi
fi
echo ""

echo "✅ Fix complete!"
echo ""

# Launch mChapters with a clean slate
open /Applications/mChapters.app

