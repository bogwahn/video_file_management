from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from .chapter_reader import read_chapters
from .utils.timecode import format_timecode, parse_timecode

DEFAULT_CHAPTERS_DIR = (
    Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc" / "Chapters"
)
DEFAULT_VIDEO_DIRS = (
    Path("/Volumes/Zetc"),
    Path("/Volumes/Torrents/Complete"),
)
VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v")
SKIP_DIR_NAMES = {".trash", ".trashes", "#recycle", "$recycle.bin"}
DEFAULT_VIDEO_LIMIT = 20
STATUS_LOG_FILENAME = "chapter_cleanup_status.txt"
STATUS_CHECKED = "checked"
STATUS_TO_CLEAN = "to_cliean"
STATUS_CLEANED = "cleaned"


@dataclass(frozen=True)
class ChapterLine:
    timecode_raw: str
    timecode_norm: str
    label: str
    label_norm: str


@dataclass(frozen=True)
class CleanupResult:
    path: Path
    status: str
    message: str


@dataclass(frozen=True)
class VideoAnalysis:
    path: Path
    chapter_count: int
    repeated_block: Optional[int]
    repeat_count: Optional[int]
    duplicate_pairs: int
    message: str


def clean_chapter_files(
    chapters_dir: Path,
    *,
    dry_run: bool = False,
) -> List[CleanupResult]:
    results: List[CleanupResult] = []
    for path in _iter_chapter_files(chapters_dir):
        lines = _read_chapter_lines(path)
        if not lines:
            results.append(CleanupResult(path=path, status="skip", message="no chapters found"))
            continue
        cleaned, repeat_count = _dedupe_chapters(lines)
        if repeat_count <= 1:
            results.append(CleanupResult(path=path, status="ok", message="no duplicates detected"))
            continue
        if dry_run:
            results.append(
                CleanupResult(
                    path=path,
                    status="dry_run",
                    message=f"would remove {repeat_count - 1} duplicate set(s)",
                )
            )
            continue
        _write_chapter_lines(path, cleaned)
        results.append(
            CleanupResult(
                path=path,
                status="fixed",
                message=f"removed {repeat_count - 1} duplicate set(s)",
            )
        )
    return results


def analyze_video_chapters(
    video_dirs: Iterable[Path],
    *,
    limit: int = DEFAULT_VIDEO_LIMIT,
) -> List[VideoAnalysis]:
    analyses: List[VideoAnalysis] = []
    for path in _iter_video_files(video_dirs):
        if len(analyses) >= limit:
            break
        read_result = read_chapters(path)
        if read_result.errors:
            analyses.append(
                VideoAnalysis(
                    path=path,
                    chapter_count=0,
                    repeated_block=None,
                    repeat_count=None,
                    duplicate_pairs=0,
                    message="; ".join(read_result.errors),
                )
            )
            continue
        entries = read_result.chapters
        normalized = [(_normalize_time_seconds(e.start_seconds), _normalize_label(e.title)) for e in entries]
        block_len, repeat_count = _find_repeated_block(normalized)
        duplicate_pairs = _count_duplicates(normalized)
        message_parts = [f"{len(entries)} chapter(s)"]
        if repeat_count and repeat_count > 1:
            message_parts.append(f"repeated block x{repeat_count}")
        if duplicate_pairs:
            message_parts.append(f"{duplicate_pairs} duplicate pair(s)")
        analyses.append(
            VideoAnalysis(
                path=path,
                chapter_count=len(entries),
                repeated_block=block_len,
                repeat_count=repeat_count,
                duplicate_pairs=duplicate_pairs,
                message=", ".join(message_parts),
            )
        )
    return analyses


def _iter_chapter_files(chapters_dir: Path) -> Iterable[Path]:
    if not chapters_dir.exists():
        return []
    return (path for path in chapters_dir.rglob("*.txt") if path.is_file() and not _should_skip_path(path))


def _read_chapter_lines(path: Path) -> List[ChapterLine]:
    lines: List[ChapterLine] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        entry = _parse_chapter_line(raw)
        if entry is not None:
            lines.append(entry)
    return lines


def _parse_chapter_line(raw: str) -> Optional[ChapterLine]:
    raw = raw.strip()
    if not raw:
        return None
    match = re.match(r"^\[(.+?)\]\s*(.*)$", raw)
    if not match:
        return None
    time_text = match.group(1).strip()
    label = match.group(2).strip()
    if not time_text:
        return None
    timecode_norm = _normalize_time_text(time_text)
    label_norm = _normalize_label(label)
    return ChapterLine(
        timecode_raw=time_text,
        timecode_norm=timecode_norm,
        label=label,
        label_norm=label_norm,
    )


def _normalize_time_text(value: str) -> str:
    try:
        return format_timecode(parse_timecode(value))
    except ValueError:
        return value


def _normalize_time_seconds(value: float) -> str:
    total_ms = int(round(value * 1000))
    seconds, millis = divmod(total_ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _normalize_label(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    return cleaned.lower()


def _dedupe_chapters(lines: Sequence[ChapterLine]) -> Tuple[List[ChapterLine], int]:
    pairs = [(line.timecode_norm, line.label_norm) for line in lines]
    block_len, repeat_count = _find_repeated_block(pairs)
    if not repeat_count or repeat_count <= 1 or not block_len:
        return list(lines), 1
    return list(lines[:block_len]), repeat_count


def _find_repeated_block(
    pairs: Sequence[Tuple[str, str]],
) -> Tuple[Optional[int], Optional[int]]:
    total = len(pairs)
    if total < 2:
        return None, None
    for block_len in range(1, total // 2 + 1):
        if total % block_len != 0:
            continue
        block = list(pairs[:block_len])
        repeated = True
        for idx in range(0, total, block_len):
            if list(pairs[idx : idx + block_len]) != block:
                repeated = False
                break
        if repeated:
            repeat_count = total // block_len
            if repeat_count > 1:
                return block_len, repeat_count
    return None, None


def _count_duplicates(pairs: Sequence[Tuple[str, str]]) -> int:
    seen: dict[Tuple[str, str], int] = {}
    dupes = 0
    for pair in pairs:
        seen[pair] = seen.get(pair, 0) + 1
    for count in seen.values():
        if count > 1:
            dupes += count - 1
    return dupes


def _write_chapter_lines(path: Path, lines: Sequence[ChapterLine]) -> None:
    output = "\n".join(f"[{line.timecode_norm}] {line.label.strip()}" for line in lines)
    output += "\n" if output else ""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(output, encoding="utf-8")
    tmp_path.replace(path)


def _iter_video_files(video_dirs: Iterable[Path]) -> Iterable[Path]:
    for root in video_dirs:
        if not root.exists() or not root.is_dir():
            continue
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


def _print_cleanup_results(results: Sequence[CleanupResult]) -> None:
    for result in results:
        print(f"{result.status}: {result.path.name} ({result.message})")


def _print_video_analysis(analyses: Sequence[VideoAnalysis]) -> None:
    for analysis in analyses:
        print(f"{analysis.path.name}: {analysis.message}")


def _load_status_log(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    entries: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.rsplit(" ", 1)
        if len(parts) != 2:
            continue
        entries[parts[0]] = parts[1]
    return entries


def _status_for_result(result: CleanupResult) -> str:
    if result.status == "fixed":
        return STATUS_CLEANED
    if result.status == "dry_run":
        return STATUS_TO_CLEAN
    return STATUS_CHECKED


def _write_status_log(path: Path, entries: dict[str, str]) -> None:
    lines = [f"{file_path} {status}" for file_path, status in sorted(entries.items())]
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def _update_status_log(results: Sequence[CleanupResult], log_path: Path) -> None:
    entries = _load_status_log(log_path)
    for result in results:
        entries[str(result.path.resolve())] = _status_for_result(result)
    _write_status_log(log_path, entries)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="chapter_cleanup")
    parser.add_argument(
        "--chapters-dir",
        type=Path,
        default=DEFAULT_CHAPTERS_DIR,
        help="Directory containing chapter text files",
    )
    parser.add_argument(
        "--video",
        action="store_true",
        help="Analyze chapter tracks in video files (no changes made)",
    )
    parser.add_argument(
        "--video-dir",
        action="append",
        default=[],
        help="Video directory to search (repeatable)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_VIDEO_LIMIT,
        help="Max number of video files to analyze",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.video:
        video_dirs = list(DEFAULT_VIDEO_DIRS)
        if args.video_dir:
            video_dirs.extend(Path(p) for p in args.video_dir)
        analyses = analyze_video_chapters(video_dirs, limit=args.limit)
        _print_video_analysis(analyses)
        return 0

    results = clean_chapter_files(args.chapters_dir, dry_run=args.dry_run)
    _print_cleanup_results(results)
    _update_status_log(results, Path.cwd() / STATUS_LOG_FILENAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
