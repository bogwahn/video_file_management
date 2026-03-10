from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Set

DEFAULT_EXTENSIONS: Set[str] = {"mp4", "mov", "m4v", "mkv"}


def _normalize_extensions(exts: Iterable[str] | None) -> Set[str]:
    if not exts:
        return set(DEFAULT_EXTENSIONS)
    return {e.strip().lower().lstrip(".") for e in exts if e.strip()}


def iter_video_files(
    root: Path,
    *,
    recursive: bool = True,
    extensions: Iterable[str] | None = None,
) -> Iterator[Path]:
    """Yield video files beneath `root` honoring recursion and extensions."""
    exts = _normalize_extensions(extensions)
    iterator = root.rglob("*") if recursive else root.iterdir()
    for path in iterator:
        if path.is_file() and path.suffix.lower().lstrip(".") in exts:
            yield path
