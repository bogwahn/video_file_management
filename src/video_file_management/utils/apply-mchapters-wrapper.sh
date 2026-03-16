#!/bin/bash
# apply-mchapters-wrapper.sh
# Safely installs (or re-installs) the MCDocStatus-clearing wrapper inside
# the mChapters app bundle. Idempotent: safe to run after every app update.
#
# The wrapper deletes the stale MCDocStatus key from the preferences plist
# on every launch, preventing the app from hanging while resolving stale
# security-scoped bookmarks for files that have moved or are unmounted.
#
# RECOVERY: If both mChapters and mChapters_bin are scripts (self-referencing
# loop), reinstall mChapters from the App Store first, then run this script.

set -euo pipefail

MACOS_DIR="/Applications/mChapters.app/Contents/MacOS"
BINARY="$MACOS_DIR/mChapters"
RENAMED="$MACOS_DIR/mChapters_bin"

echo "🔧 mChapters Wrapper Installer"
echo "=============================="
echo ""

# ── Sanity check ──────────────────────────────────────────────────────────────
# Detect the self-referencing loop: both files are scripts pointing to each
# other. This happens when the wrapper was re-applied after an update but
# mChapters_bin was already a script rather than the real Mach-O binary.
is_macho() {
    file "$1" | grep -q "Mach-O"
}

if [ -f "$RENAMED" ] && ! is_macho "$RENAMED"; then
    echo "❌ ERROR: $RENAMED is not a Mach-O binary."
    echo "   It looks like the real binary was lost (self-referencing loop)."
    echo ""
    echo "   Recovery:"
    echo "   1. Reinstall mChapters from the Mac App Store."
    echo "   2. Re-run this script."
    exit 1
fi

# ── Already wrapped? ──────────────────────────────────────────────────────────
# If mChapters_bin exists and is a real binary, the wrapper is already in
# place (or needs refreshing). Skip the rename step.
if [ -f "$RENAMED" ] && is_macho "$RENAMED"; then
    echo "ℹ️  mChapters_bin already exists and is a real binary — skipping rename."
    echo ""
elif [ -f "$BINARY" ] && is_macho "$BINARY"; then
    echo "📦 Renaming real binary → mChapters_bin..."
    sudo mv "$BINARY" "$RENAMED"
    echo "   Done"
    echo ""
else
    echo "❌ ERROR: No Mach-O binary found at $BINARY or $RENAMED."
    echo "   Please reinstall mChapters from the Mac App Store and try again."
    exit 1
fi

# ── Write wrapper ─────────────────────────────────────────────────────────────
echo "✍️  Writing wrapper script..."
sudo tee "$BINARY" > /dev/null << 'EOF'
#!/bin/bash
# mChapters launch wrapper — clears stale MCDocStatus bookmarks before launch.
# Do not replace this file; it is intentional. The real binary is mChapters_bin.
PREF_FILE="$HOME/Library/Containers/jp.tranquillitybase.mChapters/Data/Library/Preferences/jp.tranquillitybase.mChapters.plist"
/usr/libexec/PlistBuddy -c "Delete :MCDocStatus" "$PREF_FILE" 2>/dev/null || true
exec "$(dirname "$0")/mChapters_bin" "$@"
EOF
sudo chmod +x "$BINARY"
echo "   Done"
echo ""

# ── Re-sign ───────────────────────────────────────────────────────────────────
echo "🔏 Re-signing bundle ad-hoc..."
sudo codesign --force --deep --sign - /Applications/mChapters.app
echo "   Done"
echo ""

echo "✅ Wrapper installed. mChapters will clear MCDocStatus on every launch."
