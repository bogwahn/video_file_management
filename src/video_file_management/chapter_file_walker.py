from __future__ import annotations

import argparse
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from .chapter_reader import read_chapters
from .file_walker import DEFAULT_EXTENSIONS, iter_video_files
from .fix_chapters import ensure_finder_tag
from .marks.bookmarks_reader import BookmarksFileReader
from .marks.protocols import VideoMarksFile
from .marks.readers import ChaptersFileReader
from .marks.writers import MP4ChaptersWriter
from .tag_reader import read_finder_tags

DEFAULT_BOOKMARKS_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "Personal"
    / "Zetc"
    / "Bookmarks"
)
DEFAULT_CHAPTERS_DIR = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "Personal"
    / "Zetc"
    / "Chapters"
)
DEFAULT_VIDEO_DIRS = (
    Path("/Volumes/Zetc"),
    Path("/Volumes/Torrents/Complete"),
)
DEFAULT_FINDER_TAG = "Scenes:Chapters"
SUPPORTED_EMBED_EXTS = {".mp4", ".mov", ".m4v"}
RESOLUTION_TOKENS = {"2160p", "1080p", "720p", "480p", "4k", "8k", "uhd", "fhd", "hd"}


@dataclass(frozen=True)
class ChapterWalkResult:
    video_path: Path
    status: str
    message: str
    chapters_path: Optional[Path] = None
    bookmark_path: Optional[Path] = None


def walk_videos(
    paths: Optional[Iterable[Path]] = None,
    *,
    chapters_dir: Path = DEFAULT_CHAPTERS_DIR,
    bookmarks_dir: Path = DEFAULT_BOOKMARKS_DIR,
    tag: str = DEFAULT_FINDER_TAG,
    extensions: Iterable[str] | None = None,
    recursive: bool = True,
    dry_run: bool = False,
) -> List[ChapterWalkResult]:
    scan_paths = list(paths) if paths else list(DEFAULT_VIDEO_DIRS)
    exts = _normalize_extensions(extensions)
    chapters_index = _build_name_index(chapters_dir)
    bookmarks_index = _build_name_index(bookmarks_dir)

    results: List[ChapterWalkResult] = []
    for video_path in _iter_input_files(scan_paths, exts, recursive):
        results.append(
            _process_video(
                video_path,
                chapters_index=chapters_index,
                bookmarks_index=bookmarks_index,
                tag=tag,
                dry_run=dry_run,
            )
        )
    return results


def _process_video(
    video_path: Path,
    *,
    chapters_index: Dict[str, List[Path]],
    bookmarks_index: Dict[str, List[Path]],
    tag: str,
    dry_run: bool,
) -> ChapterWalkResult:
    if not video_path.exists() or not video_path.is_file():
        return ChapterWalkResult(
            video_path=video_path,
            status="missing",
            message="video file not found",
        )

    chapter_result = read_chapters(video_path)
    if chapter_result.errors:
        return ChapterWalkResult(
            video_path=video_path,
            status="error",
            message="; ".join(chapter_result.errors),
        )

    if chapter_result.chapters:
        return _ensure_tag(
            video_path,
            tag=tag,
            dry_run=dry_run,
            status="has_chapters",
        )

    chapters_path = _find_match(video_path, chapters_index)
    if chapters_path is not None:
        chapters = ChaptersFileReader().read(str(chapters_path))
        if _has_chapters(chapters):
            return _embed_and_tag(
                video_path,
                chapters,
                tag=tag,
                source_status="embedded_chapters",
                dry_run=dry_run,
                chapters_path=chapters_path,
            )
        chapters_empty = True
    else:
        chapters_empty = False

    bookmark_path = _find_match(video_path, bookmarks_index)
    if bookmark_path is not None:
        bookmarks = BookmarksFileReader().read(str(bookmark_path))
        if _has_chapters(bookmarks):
            return _embed_and_tag(
                video_path,
                bookmarks,
                tag=tag,
                source_status="embedded_bookmarks",
                dry_run=dry_run,
                bookmark_path=bookmark_path,
            )
        bookmarks_empty = True
    else:
        bookmarks_empty = False

    return ChapterWalkResult(
        video_path=video_path,
        status="empty_marks" if (chapters_empty or bookmarks_empty) else "no_match",
        message=_format_missing_message(chapters_empty, bookmarks_empty),
        chapters_path=chapters_path,
        bookmark_path=bookmark_path,
    )


def _ensure_tag(
    video_path: Path,
    *,
    tag: str,
    dry_run: bool,
    status: str,
) -> ChapterWalkResult:
    if dry_run:
        tag_present, tag_error = _has_tag(video_path, tag)
        if tag_error:
            return ChapterWalkResult(
                video_path=video_path,
                status="tag_error",
                message=tag_error,
            )
        note = "tag present" if tag_present else "tag missing"
        return ChapterWalkResult(
            video_path=video_path,
            status="dry_run",
            message=f"dry run: {note}",
        )

    added_tag, tag_err = ensure_finder_tag(video_path, tag)
    if tag_err:
        return ChapterWalkResult(
            video_path=video_path,
            status="tag_error",
            message=tag_err,
        )
    note = "tag added" if added_tag else "tag present"
    return ChapterWalkResult(
        video_path=video_path,
        status=status,
        message=note,
    )


def _embed_and_tag(
    video_path: Path,
    chapters: VideoMarksFile,
    *,
    tag: str,
    source_status: str,
    dry_run: bool,
    chapters_path: Optional[Path] = None,
    bookmark_path: Optional[Path] = None,
) -> ChapterWalkResult:
    if video_path.suffix.lower() not in SUPPORTED_EMBED_EXTS:
        return ChapterWalkResult(
            video_path=video_path,
            status="unsupported",
            message=f"unsupported container {video_path.suffix}",
            chapters_path=chapters_path,
            bookmark_path=bookmark_path,
        )

    tool_error = _check_embed_tools()
    if tool_error:
        return ChapterWalkResult(
            video_path=video_path,
            status="embed_error",
            message=tool_error,
            chapters_path=chapters_path,
            bookmark_path=bookmark_path,
        )

    if dry_run:
        return ChapterWalkResult(
            video_path=video_path,
            status="dry_run",
            message="dry run: chapters would be embedded",
            chapters_path=chapters_path,
            bookmark_path=bookmark_path,
        )

    ok, error = _embed_chapters_in_place(video_path, chapters)
    if not ok:
        return ChapterWalkResult(
            video_path=video_path,
            status="embed_failed",
            message=error or "embed failed",
            chapters_path=chapters_path,
            bookmark_path=bookmark_path,
        )

    added_tag, tag_err = ensure_finder_tag(video_path, tag)
    if tag_err:
        return ChapterWalkResult(
            video_path=video_path,
            status="tag_error",
            message=f"chapters embedded; {tag_err}",
            chapters_path=chapters_path,
            bookmark_path=bookmark_path,
        )
    note = "tag added" if added_tag else "tag present"
    return ChapterWalkResult(
        video_path=video_path,
        status=source_status,
        message=f"chapters embedded; {note}",
        chapters_path=chapters_path,
        bookmark_path=bookmark_path,
    )


def _iter_input_files(
    paths: Iterable[Path],
    extensions: Iterable[str],
    recursive: bool,
) -> Iterator[Path]:
    exts = set(extensions)
    seen: set[Path] = set()
    for raw in paths:
        path = raw.expanduser()
        if not path.exists():
            continue
        if path.is_dir():
            for candidate in iter_video_files(path, recursive=recursive, extensions=exts):
                if candidate in seen:
                    continue
                seen.add(candidate)
                yield candidate
        elif path.is_file():
            if path.suffix.lower().lstrip(".") in exts:
                if path in seen:
                    continue
                seen.add(path)
                yield path


def _normalize_extensions(exts: Iterable[str] | None) -> List[str]:
    if not exts:
        return [e.strip().lower() for e in DEFAULT_EXTENSIONS if e.strip()]
    return [e.strip().lower().lstrip(".") for e in exts if e.strip()]


def _build_name_index(root: Path) -> Dict[str, List[Path]]:
    index: Dict[str, List[Path]] = {}
    if not root.exists() or not root.is_dir():
        return index
    for path in root.rglob("*.txt"):
        if not path.is_file():
            continue
        key = _normalize_name(path.stem)
        if not key:
            continue
        index.setdefault(key, []).append(path)
    return index


def _find_match(video_path: Path, index: Dict[str, List[Path]]) -> Optional[Path]:
    key = _normalize_name(video_path.stem)
    matches = index.get(key, [])
    if not matches:
        return None
    return _pick_best_match(matches)


def _tokenize_name(name: str) -> List[str]:
    parts = re.split(r"[.\-_\s]+", name)
    return [p for p in parts if p]


def _normalize_name(value: str) -> str:
    tokens = _tokenize_name(value)
    cleaned = [t for t in tokens if not _is_bookmark_token(t) and not _is_resolution_token(t)]
    return "".join(ch for token in cleaned for ch in token.lower() if ch.isalnum())


def _is_bookmark_token(token: str) -> bool:
    return "bookmark" in token.lower()


def _is_resolution_token(token: str) -> bool:
    return token.lower() in RESOLUTION_TOKENS


def _pick_best_match(matches: Sequence[Path]) -> Path:
    return min(matches, key=lambda p: len(p.stem))


def _has_chapters(chapters: VideoMarksFile) -> bool:
    return bool(tuple(chapters.marks()))


def _check_embed_tools() -> Optional[str]:
    if shutil.which("MP4Box") is None:
        return "MP4Box not found in PATH"
    if shutil.which("ffmpeg") is None:
        return "ffmpeg not found in PATH"
    return None


def _embed_chapters_in_place(
    video_path: Path, chapters: VideoMarksFile
) -> Tuple[bool, Optional[str]]:
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


def _has_tag(path: Path, tag: str) -> Tuple[bool, Optional[str]]:
    result = read_finder_tags(path)
    if result.errors:
        return False, "; ".join(result.errors)
    return tag in result.tags, None


def _format_missing_message(chapters_empty: bool, bookmarks_empty: bool) -> str:
    if chapters_empty and bookmarks_empty:
        return "chapters and bookmarks files contained no entries"
    if chapters_empty:
        return "chapters file contained no entries"
    if bookmarks_empty:
        return "bookmarks file contained no entries"
    return "no chapters or bookmarks data found"


def _print_result(result: ChapterWalkResult) -> None:
    if result.chapters_path:
        source = f"chapters={result.chapters_path.name}"
    elif result.bookmark_path:
        source = f"bookmarks={result.bookmark_path.name}"
    else:
        source = "source=n/a"
    print(f"{result.status}: {result.video_path.name} ({source}; {result.message})")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="chapterfilewalker")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Video files or directories to scan (defaults to preset video roots)",
    )
    parser.add_argument(
        "--chapters-dir",
        type=Path,
        default=DEFAULT_CHAPTERS_DIR,
        help="Directory containing chapter text files",
    )
    parser.add_argument(
        "--bookmarks-dir",
        type=Path,
        default=DEFAULT_BOOKMARKS_DIR,
        help="Directory containing bookmarks files",
    )
    parser.add_argument("--tag", default=DEFAULT_FINDER_TAG, help="Finder tag to ensure")
    parser.add_argument(
        "--extensions",
        nargs="*",
        help="Override video file extensions (e.g. mp4 mov m4v)",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Do not recurse into subdirectories",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes")

    args = parser.parse_args(list(argv) if argv is not None else None)

    paths = [Path(p).expanduser() for p in args.paths] if args.paths else None
    results = walk_videos(
        paths,
        chapters_dir=args.chapters_dir,
        bookmarks_dir=args.bookmarks_dir,
        tag=args.tag,
        extensions=args.extensions,
        recursive=not args.non_recursive,
        dry_run=args.dry_run,
    )
    for result in results:
        _print_result(result)

    failures = [r for r in results if r.status in {"error", "embed_failed", "embed_error"}]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
