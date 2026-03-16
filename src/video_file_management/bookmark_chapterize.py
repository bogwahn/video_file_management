from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .file_walker import DEFAULT_EXTENSIONS, iter_video_files
from .fix_chapters import ensure_finder_tag
from .marks.bookmarks_reader import BookmarksFileReader
from .marks.protocols import VideoMarksFile
from .marks.writers import MP4ChaptersWriter

DEFAULT_FINDER_TAG = "Scenes:Chapters"
DEFAULT_ZETC_DIR = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc"
DEFAULT_VIDEO_DIRS = (
    DEFAULT_ZETC_DIR,
    Path.home() / "Movies",
    Path.home() / "Downloads",
)
BOOKMARK_SUFFIXES = ("-bookmarks", "_bookmarks")


@dataclass(frozen=True)
class BookmarkChapterizeResult:
    bookmark_path: Path
    video_path: Path | None
    output_path: Path | None
    status: str
    message: str


def chapterize_bookmark(
    bookmark_path: Path,
    *,
    search_dirs: Iterable[Path] = DEFAULT_VIDEO_DIRS,
    output_path: Path | None = None,
    output_dir: Path | None = None,
    extensions: Iterable[str] | None = None,
    tag: str = DEFAULT_FINDER_TAG,
    dry_run: bool = False,
    video_files: Sequence[Path] | None = None,
) -> BookmarkChapterizeResult:
    if output_path is not None and output_dir is not None:
        return BookmarkChapterizeResult(
            bookmark_path=bookmark_path,
            video_path=None,
            output_path=None,
            status="invalid_output",
            message="Provide either output_path or output_dir, not both.",
        )

    resolved_bookmark = _resolve_bookmark_path(bookmark_path)
    if resolved_bookmark is None:
        return BookmarkChapterizeResult(
            bookmark_path=bookmark_path,
            video_path=None,
            output_path=None,
            status="missing_bookmark",
            message="Bookmark file not found.",
        )

    chapters = _read_bookmarks(resolved_bookmark)
    if not _has_chapters(chapters):
        return BookmarkChapterizeResult(
            bookmark_path=resolved_bookmark,
            video_path=None,
            output_path=None,
            status="no_chapters",
            message="No chapters found in bookmark file.",
        )

    candidate_videos = video_files or _collect_video_files(search_dirs, extensions)
    video_path = _find_video_match(resolved_bookmark, candidate_videos)
    if video_path is None:
        return BookmarkChapterizeResult(
            bookmark_path=resolved_bookmark,
            video_path=None,
            output_path=None,
            status="no_video",
            message="No matching video found in search directories.",
        )

    resolved_output = _resolve_output_path(video_path, output_path, output_dir)
    if dry_run:
        return BookmarkChapterizeResult(
            bookmark_path=resolved_bookmark,
            video_path=video_path,
            output_path=resolved_output,
            status="dry_run",
            message="Dry run: no changes written.",
        )

    _embed_chapters(video_path, chapters, resolved_output)
    if resolved_output is not None and not resolved_output.exists():
        return BookmarkChapterizeResult(
            bookmark_path=resolved_bookmark,
            video_path=video_path,
            output_path=resolved_output,
            status="embed_failed",
            message="Output file was not created.",
        )
    tag_path = resolved_output or video_path
    added_tag, tag_err = ensure_finder_tag(tag_path, tag)
    if tag_err:
        return BookmarkChapterizeResult(
            bookmark_path=resolved_bookmark,
            video_path=video_path,
            output_path=resolved_output,
            status="tag_error",
            message=tag_err,
        )

    tag_note = "tag added" if added_tag else "tag already present"
    return BookmarkChapterizeResult(
        bookmark_path=resolved_bookmark,
        video_path=video_path,
        output_path=resolved_output,
        status="embedded",
        message=f"Chapters embedded; {tag_note}.",
    )


def chapterize_bookmarks(
    bookmark_paths: Iterable[Path],
    *,
    search_dirs: Iterable[Path] = DEFAULT_VIDEO_DIRS,
    output_dir: Path | None = None,
    extensions: Iterable[str] | None = None,
    tag: str = DEFAULT_FINDER_TAG,
    dry_run: bool = False,
) -> List[BookmarkChapterizeResult]:
    video_files = _collect_video_files(search_dirs, extensions)
    results: List[BookmarkChapterizeResult] = []
    for bookmark_path in bookmark_paths:
        results.append(
            chapterize_bookmark(
                bookmark_path,
                search_dirs=search_dirs,
                output_dir=output_dir,
                extensions=extensions,
                tag=tag,
                dry_run=dry_run,
                video_files=video_files,
            )
        )
    return results


def _resolve_bookmark_path(bookmark_path: Path) -> Path | None:
    if bookmark_path.exists() and bookmark_path.is_file():
        return bookmark_path
    return None


def _read_bookmarks(bookmark_path: Path) -> VideoMarksFile:
    reader = BookmarksFileReader()
    return reader.read(str(bookmark_path))


def _has_chapters(chapters: VideoMarksFile) -> bool:
    return bool(tuple(chapters.marks()))


def _collect_video_files(
    search_dirs: Iterable[Path],
    extensions: Iterable[str] | None,
) -> List[Path]:
    exts = extensions or DEFAULT_EXTENSIONS
    seen: set[Path] = set()
    candidates: List[Path] = []
    for root in search_dirs:
        if not root.exists() or not root.is_dir():
            continue
        for path in iter_video_files(root, recursive=True, extensions=exts):
            if path in seen:
                continue
            seen.add(path)
            candidates.append(path)
    return candidates


def _find_video_match(bookmark_path: Path, candidates: Sequence[Path]) -> Path | None:
    target_stem = _derive_target_stem(bookmark_path)
    if not target_stem:
        return None
    target_key = _normalize_name(target_stem)
    if not target_key:
        return None
    substring_matches: List[Path] = []
    for candidate in candidates:
        candidate_key = _normalize_name(candidate.stem)
        if candidate_key == target_key:
            return candidate
        if target_key in candidate_key:
            substring_matches.append(candidate)
    if substring_matches:
        return min(substring_matches, key=lambda p: len(p.stem))
    return None


def _derive_target_stem(bookmark_path: Path) -> str:
    name = bookmark_path.stem
    for suffix in BOOKMARK_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _normalize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _resolve_output_path(
    video_path: Path,
    output_path: Path | None,
    output_dir: Path | None,
) -> Path | None:
    if output_path is not None:
        return output_path
    if output_dir is not None:
        return output_dir / video_path.name
    return None


def _embed_chapters(
    video_path: Path,
    chapters: VideoMarksFile,
    output_path: Path | None,
) -> None:
    writer = MP4ChaptersWriter()
    writer.write(
        str(video_path),
        chapters,
        output_path=str(output_path) if output_path is not None else None,
    )


def _expand_bookmark_inputs(paths: Iterable[str]) -> List[Path]:
    expanded: List[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_dir():
            for candidate in path.rglob("*.txt"):
                if candidate.is_file():
                    expanded.append(candidate)
        else:
            expanded.append(path)
    return expanded


def _print_result(result: BookmarkChapterizeResult) -> None:
    target = result.output_path or result.video_path
    target_desc = str(target) if target is not None else "n/a"
    print(f"{result.status}: {result.bookmark_path.name} -> {target_desc} ({result.message})")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bookmark_chapterize")
    parser.add_argument("bookmarks", nargs="+", help="Bookmarks files or folders")
    parser.add_argument(
        "--video-dir",
        action="append",
        default=[],
        help="Additional directory to search for videos (repeatable)",
    )
    parser.add_argument("--output", help="Output video path (single bookmark only)")
    parser.add_argument(
        "--output-dir",
        help="Directory for output copies (mirrors video filename)",
    )
    parser.add_argument("--tag", default=DEFAULT_FINDER_TAG, help="Finder tag to ensure")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes")

    args = parser.parse_args(argv)

    bookmark_paths = _expand_bookmark_inputs(args.bookmarks)
    if not bookmark_paths:
        print("No bookmark files found.")
        return 1

    output_path = Path(args.output).expanduser() if args.output else None
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else None
    if output_path is not None and len(bookmark_paths) != 1:
        print("`--output` only supports a single bookmark file.")
        return 2

    search_dirs = list(DEFAULT_VIDEO_DIRS)
    if args.video_dir:
        search_dirs.extend(Path(p).expanduser() for p in args.video_dir)

    if output_path is not None:
        result = chapterize_bookmark(
            bookmark_paths[0],
            search_dirs=search_dirs,
            output_path=output_path,
            tag=args.tag,
            dry_run=args.dry_run,
        )
        _print_result(result)
        return 0 if result.status in {"embedded", "dry_run"} else 1

    results = chapterize_bookmarks(
        bookmark_paths,
        search_dirs=search_dirs,
        output_dir=output_dir,
        tag=args.tag,
        dry_run=args.dry_run,
    )
    for result in results:
        _print_result(result)

    has_failure = any(r.status not in {"embedded", "dry_run"} for r in results)
    return 1 if has_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
