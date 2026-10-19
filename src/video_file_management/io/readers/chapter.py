from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass(slots=True)
class ChapterEntry:
    start_seconds: float
    title: str


@dataclass(slots=True)
class ChapterReadResult:
    chapters: List[ChapterEntry] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _run_ffprobe(path: Path) -> Tuple[Optional[dict], Optional[str]]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None, "ffprobe not found in PATH"
    try:
        res = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_chapters",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"ffprobe error: {exc}"

    try:
        return json.loads(res.stdout or "{}"), None
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"ffprobe parse error: {exc}"


def read_chapters(path: Path) -> ChapterReadResult:
    result = ChapterReadResult()
    data, err = _run_ffprobe(path)
    if err:
        result.errors.append(err)
        return result
    if not data:
        result.errors.append("ffprobe returned no data")
        return result

    chapters_data = data.get("chapters", []) or []
    for entry in chapters_data:
        try:
            start = float(entry.get("start", 0.0))
            title = ""
            if isinstance(entry, dict):
                raw_tags = entry.get("tags")
                tags = raw_tags if isinstance(raw_tags, dict) else {}
                title = tags.get("title") or tags.get("TITLE") or entry.get("title") or ""
            result.chapters.append(ChapterEntry(start_seconds=start, title=title))
        except Exception:
            result.errors.append("chapter parse failed")
            continue

    return result
