from __future__ import annotations

import json
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .marks.chapters_file import ChaptersFile
from .marks.writers import MP4ChaptersWriter
from .utils.timecode import format_timecode


def ffprobe_chapters(video_path: Path) -> List[Dict]:
    """Return list of chapters from ffprobe as dicts with start (seconds) and title."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found in PATH")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_chapters",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return []
    try:
        data = json.loads(res.stdout or "{}")
        return list(data.get("chapters", []))
    except Exception:
        return []


def detect_reset_index(chapters: List[Dict]) -> Optional[int]:
    """Detect if chapters reset mid-list. Return index of first entry in second set, or None."""
    if not chapters:
        return None
    prev = float(chapters[0].get("start", 0))
    for i in range(1, len(chapters)):
        cur = float(chapters[i].get("start", 0))
        # Strictly less indicates a reset to start
        if cur < prev:
            return i
        prev = cur
    return None


def ensure_finder_tag(path: Path, tag: str = "Scenes:Chapters") -> Tuple[bool, Optional[str]]:
    """Ensure Finder tag exists on file. Returns (added, error_message).

    Uses the `xattr` CLI with binary plist encoding for
    `com.apple.metadata:_kMDItemUserTags` to avoid extra dependencies.
    """
    import plistlib

    xattr_key = "com.apple.metadata:_kMDItemUserTags"
    existing_tags: List[str] = []

    try:
        result = subprocess.run(
            ["xattr", "-px", xattr_key, str(path)],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            hex_value = result.stdout.strip().decode("utf-8", errors="ignore")
            if hex_value:
                raw = bytes.fromhex(hex_value)
                existing_tags = list(plistlib.loads(raw))
    except Exception as exc:
        return False, f"Failed to read existing tags: {exc}"

    normalized = [t for t in existing_tags if t not in {"Chapters", "Scenes/Chapters"}]
    if tag in normalized:
        return False, None
    normalized.append(tag)

    try:
        plist_data = plistlib.dumps(normalized, fmt=plistlib.FMT_BINARY)
        subprocess.run(
            [
                "xattr",
                "-wx",
                xattr_key,
                plist_data.hex(),
                str(path),
            ],
            check=True,
        )
        return True, None
    except Exception as exc:
        return False, f"Failed to write tag: {exc}"


def fix_file(video_path: Path) -> Optional[Dict]:
    """Inspect and fix chapters for a single video file.

    Returns a report dict if changes were made, otherwise None.
    """
    chapters = ffprobe_chapters(video_path)
    if not chapters:
        return None

    reset_idx = detect_reset_index(chapters)
    removed = 0
    added = 0
    tag_added = False
    if reset_idx is not None:
        # Keep entries up to reset_idx
        kept = chapters[:reset_idx]

        # Build a ChaptersFile from kept entries
        cf = ChaptersFile(str(video_path))
        for ch in kept:
            start = float(ch.get("start", 0.0))
            title = ch.get("tags", {}).get("title") if isinstance(ch.get("tags"), dict) else None
            if title is None:
                # Some files store title at chapter['tag']['title'] or chapter['title']
                title = (
                    ch.get("title") or ch.get("tags", {}).get("TITLE")
                    if isinstance(ch.get("tags"), dict)
                    else ch.get("title")
                )
            if title is None:
                title = ""
            td = timedelta(seconds=start)
            tc = format_timecode(td)
            cf.add(tc, title)

        # Re-embed chapters using MP4ChaptersWriter
        writer = MP4ChaptersWriter()
        writer.write(str(video_path), cf)

        removed = len(chapters) - len(kept)
        added = len(kept)

    # Ensure Finder tag `Scenes:Chapters` present (and normalize other chapter tags)
    # Normalization: remove tags 'Chapters' or 'Scenes/Chapters' and add 'Scenes:Chapters'
    # Practical operation: attempt to add Scenes:Chapters; if added, note it
    added_tag, tag_err = ensure_finder_tag(video_path, "Scenes:Chapters")
    if added_tag:
        tag_added = True

    if removed > 0 or tag_added:
        return {
            "path": str(video_path),
            "removed": removed,
            "kept": added,
            "tag_added": tag_added,
            "tag_error": tag_err,
        }
    return None


def find_video_files(paths: List[Path]) -> List[Path]:
    exts = {"mp4", "mov", "m4v", "mkv"}
    out: List[Path] = []
    for p in paths:
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower().lstrip(".") in exts:
                    out.append(f)
        elif p.exists() and p.is_file() and p.suffix.lower().lstrip(".") in exts:
            out.append(p)
    return out


def main_cli(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="fix_chapters")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument("--report", help="Path to write JSON report", default=None)
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.paths]
    files = find_video_files(paths)
    reports = []
    for f in files:
        try:
            r = fix_file(f)
            if r:
                reports.append(r)
                print(f"Fixed: {r['path']} removed={r['removed']} kept={r['kept']} tag_added={r['tag_added']}")
        except Exception as exc:
            print(f"Error processing {f}: {exc}")

    if args.report:
        try:
            Path(args.report).write_text(json.dumps(reports, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"Failed to write report: {exc}")

    # Summary
    print("\nSummary:")
    for r in reports:
        print(f"{r['path']}: removed={r['removed']} kept={r['kept']} tag_added={r['tag_added']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
