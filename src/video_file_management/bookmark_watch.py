from __future__ import annotations

import argparse
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from .chapter_reader import read_chapters
from .fix_chapters import ensure_finder_tag
from .marks.bookmarks_reader import BookmarksFileReader
from .marks.protocols import VideoMarksFile
from .marks.writers import MP4ChaptersWriter

DEFAULT_BOOKMARKS_DIR = (
    Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc" / "Bookmarks"
)
DEFAULT_CHAPTERS_DIR = (
    Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc" / "Chapters"
)
DEFAULT_VIDEO_DIRS = (
    Path("/Volumes/Zetc"),
    Path("/Volumes/Torrents/Complete"),
)
DEFAULT_POLL_SECONDS = 5.0
DEFAULT_FINDER_TAG = "Scenes:Chapters"
VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v")
SKIP_DIR_NAMES = {".trash", ".trashes", "#recycle", "$recycle.bin"}
RESOLUTION_TOKENS = {"2160p", "1080p", "720p", "480p", "4k", "8k", "uhd", "fhd", "hd"}


@dataclass(frozen=True)
class BookmarkProcessResult:
    bookmark_path: Path
    chapters_path: Optional[Path]
    video_path: Optional[Path]
    status: str
    message: str


def process_bookmark(
    bookmark_path: Path,
    *,
    chapters_dir: Path = DEFAULT_CHAPTERS_DIR,
    video_dirs: Iterable[Path] = DEFAULT_VIDEO_DIRS,
    tag: str = DEFAULT_FINDER_TAG,
    dry_run: bool = False,
) -> BookmarkProcessResult:
    if not bookmark_path.exists() or not bookmark_path.is_file():
        return BookmarkProcessResult(
            bookmark_path=bookmark_path,
            chapters_path=None,
            video_path=None,
            status="missing",
            message="bookmark file not found",
        )

    chapters = _read_bookmarks(bookmark_path)
    if not _has_chapters(chapters):
        return BookmarkProcessResult(
            bookmark_path=bookmark_path,
            chapters_path=None,
            video_path=None,
            status="empty",
            message="no chapters in bookmark file",
        )

    base_name = _derive_base_name(bookmark_path)
    chapters_path = chapters_dir / f"{base_name}.txt"
    if not dry_run:
        chapters_dir.mkdir(parents=True, exist_ok=True)
        chapters_path.write_text(chapters.to_string(), encoding="utf-8")

    video_path = _find_video_file(base_name, video_dirs)
    if video_path is None:
        return BookmarkProcessResult(
            bookmark_path=bookmark_path,
            chapters_path=chapters_path,
            video_path=None,
            status="no_video",
            message="no matching video found",
        )

    if dry_run:
        return BookmarkProcessResult(
            bookmark_path=bookmark_path,
            chapters_path=chapters_path,
            video_path=video_path,
            status="dry_run",
            message="dry run: no changes applied",
        )

    ok, error = _embed_chapters_in_place(video_path, chapters)
    if not ok:
        return BookmarkProcessResult(
            bookmark_path=bookmark_path,
            chapters_path=chapters_path,
            video_path=video_path,
            status="embed_failed",
            message=error or "embed failed",
        )

    added_tag, tag_err = ensure_finder_tag(video_path, tag)
    if tag_err:
        return BookmarkProcessResult(
            bookmark_path=bookmark_path,
            chapters_path=chapters_path,
            video_path=video_path,
            status="tag_error",
            message=tag_err,
        )

    tag_note = "tag added" if added_tag else "tag present"
    return BookmarkProcessResult(
        bookmark_path=bookmark_path,
        chapters_path=chapters_path,
        video_path=video_path,
        status="ok",
        message=f"chapters embedded; {tag_note}",
    )


def watch_bookmarks(
    bookmarks_dir: Path,
    *,
    chapters_dir: Path = DEFAULT_CHAPTERS_DIR,
    video_dirs: Iterable[Path] = DEFAULT_VIDEO_DIRS,
    interval_seconds: float = DEFAULT_POLL_SECONDS,
    tag: str = DEFAULT_FINDER_TAG,
    process_existing: bool = True,
    dry_run: bool = False,
) -> None:
    last_seen: dict[Path, float] = {}
    if not process_existing and bookmarks_dir.exists():
        for path in _iter_bookmark_files(bookmarks_dir):
            try:
                last_seen[path] = path.stat().st_mtime
            except FileNotFoundError:
                continue

    print(f"Watching {bookmarks_dir} for bookmark changes...")
    while True:
        try:
            for path in _iter_bookmark_files(bookmarks_dir):
                try:
                    mtime = path.stat().st_mtime
                except FileNotFoundError:
                    continue
                if last_seen.get(path) == mtime:
                    continue
                result = process_bookmark(
                    path,
                    chapters_dir=chapters_dir,
                    video_dirs=video_dirs,
                    tag=tag,
                    dry_run=dry_run,
                )
                last_seen[path] = mtime
                _print_result(result)
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("Stopping bookmark watcher.")
            return


def _iter_bookmark_files(bookmarks_dir: Path) -> Iterable[Path]:
    if not bookmarks_dir.exists():
        return []
    return (path for path in bookmarks_dir.rglob("*.txt") if path.is_file() and not _should_skip_path(path))


def _read_bookmarks(bookmark_path: Path) -> VideoMarksFile:
    reader = BookmarksFileReader()
    return reader.read(str(bookmark_path))


def _has_chapters(chapters: VideoMarksFile) -> bool:
    return bool(tuple(chapters.marks()))


def _find_video_file(base_name: str, video_dirs: Iterable[Path]) -> Optional[Path]:
    target_key = _normalize_name(base_name)
    if not target_key:
        return None
    exact_matches: List[Path] = []
    fuzzy_matches: List[Path] = []
    for root in video_dirs:
        for candidate in _iter_video_files(root):
            candidate_key = _normalize_name(candidate.stem)
            if not candidate_key:
                continue
            if candidate_key == target_key:
                exact_matches.append(candidate)
                continue
            if target_key in candidate_key or candidate_key in target_key:
                fuzzy_matches.append(candidate)
    if exact_matches:
        return _pick_best_match(exact_matches)
    if fuzzy_matches:
        return _pick_best_match(fuzzy_matches)
    return None


def _iter_video_files(root: Path) -> Iterable[Path]:
    if not root.exists() or not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir_name(d)]
        for filename in filenames:
            if not filename:
                continue
            if filename.startswith("."):
                continue
            if Path(filename).suffix.lower() in VIDEO_EXTENSIONS:
                yield Path(dirpath) / filename


def _should_skip_dir_name(name: str) -> bool:
    return name.lower() in SKIP_DIR_NAMES


def _should_skip_path(path: Path) -> bool:
    return any(_should_skip_dir_name(part) for part in path.parts)


def _derive_base_name(bookmark_path: Path) -> str:
    tokens = _tokenize_name(bookmark_path.stem)
    cleaned = [t for t in tokens if not _is_bookmark_token(t) and not _is_resolution_token(t)]
    if cleaned:
        return _safe_filename_component(" ".join(cleaned))
    fallback = _safe_filename_component(bookmark_path.stem)
    return fallback.replace("bookmarks", "").replace("Bookmarks", "").strip(" -_")


def _tokenize_name(name: str) -> List[str]:
    parts = re.split(r"[.\-_\s]+", name)
    return [p for p in parts if p]


def _is_bookmark_token(token: str) -> bool:
    return "bookmark" in token.lower()


def _is_resolution_token(token: str) -> bool:
    return token.lower() in RESOLUTION_TOKENS


def _normalize_name(value: str) -> str:
    tokens = _tokenize_name(value)
    cleaned = [t for t in tokens if not _is_bookmark_token(t) and not _is_resolution_token(t)]
    return "".join(ch for token in cleaned for ch in token.lower() if ch.isalnum())


def _safe_filename_component(value: str) -> str:
    return value.replace("/", "_")


def _pick_best_match(matches: Sequence[Path]) -> Path:
    return min(matches, key=lambda p: len(p.stem))


def _embed_chapters_in_place(video_path: Path, chapters: VideoMarksFile) -> Tuple[bool, Optional[str]]:
    expected_count = len(tuple(chapters.marks()))
    temp_output = video_path.with_name(f"{video_path.stem}.chaptered{video_path.suffix}")
    writer = MP4ChaptersWriter()
    writer.write(str(video_path), chapters, output_path=str(temp_output))
    if not temp_output.exists() or temp_output.stat().st_size == 0:
        return False, "chaptered output missing"

    verified, verify_err = _verify_chaptered_file(temp_output, expected_count)
    if not verified:
        try:
            temp_output.unlink()
        except Exception:
            pass
        return False, verify_err
    try:
        _replace_original(video_path, temp_output)
    except Exception as exc:
        return False, f"replace failed: {exc}"
    return True, None


def _verify_chaptered_file(path: Path, expected_count: int) -> Tuple[bool, Optional[str]]:
    result = read_chapters(path)
    if result.errors:
        return False, "; ".join(result.errors)
    if expected_count and len(result.chapters) < expected_count:
        return False, "chapter verification failed"
    return True, None


def _replace_original(original: Path, replacement: Path) -> None:
    backup = original.with_suffix(original.suffix + ".bak")
    try:
        if backup.exists():
            backup.unlink()
        original.replace(backup)
        replacement.replace(original)
        try:
            backup.unlink()
        except Exception:
            pass
    except Exception:
        if backup.exists() and not original.exists():
            backup.replace(original)
        raise


def _print_result(result: BookmarkProcessResult) -> None:
    target = result.video_path.name if result.video_path else "n/a"
    print(f"{result.status}: {result.bookmark_path.name} -> {target} ({result.message})")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="watch_bookmarks")
    parser.add_argument(
        "--bookmarks-dir",
        type=Path,
        default=DEFAULT_BOOKMARKS_DIR,
        help="Directory to watch for bookmark files",
    )
    parser.add_argument(
        "--chapters-dir",
        type=Path,
        default=DEFAULT_CHAPTERS_DIR,
        help="Directory to write chapter files",
    )
    parser.add_argument(
        "--video-dir",
        action="append",
        default=[],
        help="Video directory to search (repeatable)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_POLL_SECONDS,
        help="Polling interval in seconds",
    )
    parser.add_argument("--tag", default=DEFAULT_FINDER_TAG, help="Finder tag to ensure")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Do not process existing bookmark files on startup",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes")

    args = parser.parse_args(list(argv) if argv is not None else None)
    video_dirs = list(DEFAULT_VIDEO_DIRS)
    if args.video_dir:
        video_dirs.extend(Path(p) for p in args.video_dir)

    watch_bookmarks(
        args.bookmarks_dir,
        chapters_dir=args.chapters_dir,
        video_dirs=video_dirs,
        interval_seconds=args.interval,
        tag=args.tag,
        process_existing=not args.skip_existing,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
