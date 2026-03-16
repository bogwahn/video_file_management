# mChapters Fix

## Problem

mChapters stores a `MCDocStatus` key in its preferences plist containing security-scoped
bookmarks for every previously opened file. On launch, the app tries to resolve these
bookmarks before showing the main window. If any bookmark points to a file that has moved,
been deleted, or is on an unmounted volume, macOS blocks the launch indefinitely — the app
appears open in the Dock but the main window never surfaces.

## Root Cause

The `MCDocStatus` key in:
```
~/Library/Containers/jp.tranquillitybase.mChapters/Data/Library/Preferences/jp.tranquillitybase.mChapters.plist
```

accumulates stale bookmarks across sessions. Video files are large and frequently live on
external drives or network shares that aren't always mounted, making stale entries inevitable.

## Fix

`MCDocStatus` is a "restore previous session" mechanism with no meaningful value for a video
chapter editor — you always know which file you want when you open the app. Clearing it on
every launch is safe; all other preferences (window layout, column sizes, UI state) are
stored in separate keys and are untouched.

### Automatic fix (current setup)

The real mChapters binary at `/Applications/mChapters.app/Contents/MacOS/mChapters_bin` is
wrapped by a shell script at `/Applications/mChapters.app/Contents/MacOS/mChapters` that
deletes `MCDocStatus` via PlistBuddy before handing off to the real binary:

```bash
#!/bin/bash
PREF_FILE="$HOME/Library/Containers/jp.tranquillitybase.mChapters/Data/Library/Preferences/jp.tranquillitybase.mChapters.plist"
/usr/libexec/PlistBuddy -c "Delete :MCDocStatus" "$PREF_FILE" 2>/dev/null || true
exec "$(dirname "$0")/mChapters_bin" "$@"
```

The bundle is re-signed ad-hoc. This runs transparently on every launch with no extra icons
or visible steps.

### Manual fix

If mChapters is stuck right now, run:
```bash
bash src/video_file_management/utils/fix-mchapters.sh
```

This kills the app, clears `MCDocStatus` and the LaunchServices recent documents list,
restarts `cfprefsd`, verifies the fix, and relaunches mChapters.

## After a mChapters App Update

App updates overwrite the bundle, removing the wrapper. Re-apply using the
idempotent installer script — it verifies the binary is real before touching
anything:

```bash
bash src/video_file_management/utils/apply-mchapters-wrapper.sh
```

The script detects whether `mChapters_bin` already exists and is a real
Mach-O binary, skipping the rename step if so. Safe to run after every update.

## Recovery: self-referencing loop (binary lost)

This happens when the wrapper is re-applied after an update, but `mChapters_bin`
was already a script rather than the real binary — both files end up as the same
bash script calling each other. Symptoms: mChapters immediately shows as running
in Activity Monitor but no window appears; `file mChapters_bin` returns "shell
script" instead of "Mach-O".

**Fix:**

```bash
# 1. Reinstall mChapters from the Mac App Store to restore the real binary
open "macappstores://apps.apple.com/app/mchapters/id1487020685"

# 2. Once reinstalled, re-apply the wrapper
bash src/video_file_management/utils/apply-mchapters-wrapper.sh
```

The `apply-mchapters-wrapper.sh` script will refuse to proceed and print a
clear error if `mChapters_bin` is not a real Mach-O binary, preventing this
from happening again.
