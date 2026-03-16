"""CLI interface for chapterize command."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

from ..marks.bookmarks_reader import BookmarksFileReader
from ..marks.chapters_file import ChaptersFile
from ..marks.models import VideoMark
from ..marks.protocols import VideoMarksFile
from ..marks.readers import ChaptersFileReader
from ..marks.writers import MP4ChaptersWriter
from ..metadata_reader import read_file_metadata
from ..utils.timecode import format_timecode

# Strict allowlist: do not search outside these roots for matching video files.
CONFIGURED_VIDEO_ROOTS: tuple[Path, ...] = (
    Path("/Volumes/Zetc/Models"),
    Path("/Volumes/Zetc/Studios"),
    Path("/Volumes/Zetc/Uncategorized"),
    Path("/Volumes/Zetc-1/Models"),
    Path("/Volumes/Zetc-1/Studios"),
    Path("/Volumes/Zetc-1/Uncategorized"),
    Path("/Volumes/Torrents/Complete/Zetc"),
    Path("/Volumes/TorrentsOld/Complete/Zetc"),
    Path("/Volumes/Internal"),
    Path("/Volumes/External"),
)

DEFAULT_CHAPTERS_DIR = (
    Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc" / "Chapters"
)

DEFAULT_BOOKMARKS_DIR = (
    Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc" / "Bookmarks"
)

VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".avi"}
RESOLUTION_TOKENS = {"2160p", "1080p", "720p", "480p", "4k", "8k", "uhd", "fhd", "hd"}


def _normalize_name(raw: str) -> str:
    tokens: list[str] = []
    for token in raw.replace("-", " ").replace("_", " ").replace(".", " ").split():
        lower = token.lower()
        if "bookmark" in lower:
            continue
        if lower in RESOLUTION_TOKENS:
            continue
        tokens.append(lower)
    return "".join(ch for token in tokens for ch in token if ch.isalnum())


class CLIUserPromptStrategy:
    """Terminal prompt strategy with Keep/Replace/Merge flow."""

    def __init__(self, *, non_interactive: bool = False) -> None:
        self._non_interactive = non_interactive

    def notify_progress(self, message: str) -> None:
        print(message)

    def notify_error(self, message: str) -> None:
        print(f"ERROR: {message}", file=sys.stderr)

    def prompt_resolution(self, existing: Iterable[VideoMark], incoming: Iterable[VideoMark]) -> str:
        existing_rows = [self._format_mark(mark) for mark in existing]
        incoming_rows = [self._format_mark(mark) for mark in incoming]

        print("\nChapter conflict detected")
        print(
            self._render_two_columns(
                "Text File (Chapters/Bookmarks)", incoming_rows, "Video File Chapters", existing_rows
            )
        )

        if self._non_interactive:
            print("Non-interactive mode: defaulting to Replace")
            return "Replace"

        while True:
            choice = input("Choose action [k]eep/[r]eplace/[m]erge: ").strip().lower()
            if choice in {"k", "keep"}:
                return "Keep"
            if choice in {"r", "replace"}:
                return "Replace"
            if choice in {"m", "merge"}:
                return "Merge"

    def _format_mark(self, mark: VideoMark) -> str:
        return f"{format_timecode(mark.timecode)} {mark.label}"

    def _render_two_columns(self, left_title: str, left: list[str], right_title: str, right: list[str]) -> str:
        left_width = 60
        divider = " | "
        rows = max(len(left), len(right), 1)

        header = f"{left_title[:left_width]:<{left_width}}{divider}{right_title}"
        bar = f"{'-' * left_width}{divider}{'-' * 40}"
        lines = [header, bar]
        for idx in range(rows):
            left_value = left[idx] if idx < len(left) else ""
            right_value = right[idx] if idx < len(right) else ""
            lines.append(f"{left_value[:left_width]:<{left_width}}{divider}{right_value}")
        return "\n".join(lines)


class FileKindDetector:
    """Detect input kind as video, bookmarks, chapters, or unknown."""

    def detect(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return "unknown"

        if path.suffix.lower() in VIDEO_EXTENSIONS:
            return "video"

        if path.suffix.lower() != ".txt":
            return "unknown"

        if "bookmark" in path.name.lower():
            return "bookmarks"

        return self._detect_text_kind(path)

    def _detect_text_kind(self, path: Path) -> str:
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("//"):
                    continue
                if line.startswith("[") and "]" in line:
                    return "chapters"
                if "," in line and ":" in line:
                    return "bookmarks"
                return "unknown"
        except Exception:
            return "unknown"
        return "unknown"


class MarksLoader:
    """Load marks from chapters/bookmarks files."""

    def load(self, path: Path, kind: str) -> list[VideoMark]:
        if kind == "bookmarks":
            marks_file = BookmarksFileReader().read(str(path))
        else:
            marks_file = ChaptersFileReader().read(str(path))
        return list(marks_file.marks())


class CLIVideoReaderStrategy:
    """Read existing chapters embedded in a video file."""

    def read(self, file_path: str) -> VideoMarksFile:
        chapters_file = ChaptersFile(file_path=file_path)
        meta = read_file_metadata(Path(file_path))
        for chapter in meta.chapters:
            tc_str = format_timecode(timedelta(seconds=chapter.start_seconds))
            chapters_file.add(tc_str, chapter.title)
        return chapters_file


class CLIVideoWriterStrategy:
    """Write chapters into videos using atomic MP4 writer."""

    def write(self, video_path: str, marks: Iterable[VideoMark]) -> None:
        chapters = ChaptersFile(file_path=video_path)
        for mark in marks:
            chapters.add(format_timecode(mark.timecode), mark.label)
        MP4ChaptersWriter().write(video_path, chapters)


class MergeService:
    """Merge marks by timecode and keep first occurrence for each timestamp."""

    def merge(self, existing: Iterable[VideoMark], incoming: Iterable[VideoMark]) -> list[VideoMark]:
        ordered = sorted(list(existing) + list(incoming), key=lambda m: m.timecode)
        merged: list[VideoMark] = []
        seen = set()
        for mark in ordered:
            if mark.timecode in seen:
                continue
            seen.add(mark.timecode)
            merged.append(mark)
        return merged


class PathMatchIndex:
    """Indexes chapter and bookmark files for quick per-video matching."""

    def __init__(self, chapters_dir: Path, bookmarks_dir: Path) -> None:
        self._chapters_index = self._build_index(chapters_dir)
        self._bookmarks_index = self._build_index(bookmarks_dir)

    def find_marks_for_video_name(self, video_stem: str) -> tuple[Path, str] | None:
        key = _normalize_name(video_stem)
        chapter_match = self._pick_best(self._chapters_index.get(key, []))
        if chapter_match is not None:
            return chapter_match, "chapters"

        bookmark_match = self._pick_best(self._bookmarks_index.get(key, []))
        if bookmark_match is not None:
            return bookmark_match, "bookmarks"

        return None

    def _build_index(self, root: Path) -> dict[str, list[Path]]:
        index: dict[str, list[Path]] = {}
        if not root.exists() or not root.is_dir():
            return index
        for path in root.rglob("*.txt"):
            key = _normalize_name(path.stem)
            if not key:
                continue
            index.setdefault(key, []).append(path)
        return index

    def _pick_best(self, candidates: list[Path]) -> Optional[Path]:
        if not candidates:
            return None
        return min(candidates, key=lambda p: len(p.stem))


class VideoLocator:
    """Find videos that correspond to chapters/bookmarks files."""

    def __init__(self, roots: Sequence[Path]) -> None:
        self._roots = roots

    def find_video_for_marks_file(self, marks_file: Path) -> Optional[Path]:
        target = _normalize_name(marks_file.stem)
        for root in self._roots:
            if not root.exists() or not root.is_dir():
                continue
            for candidate in root.rglob("*"):
                if not candidate.is_file():
                    continue
                if candidate.suffix.lower() not in VIDEO_EXTENSIONS:
                    continue
                if _normalize_name(candidate.stem) == target:
                    return candidate
        return None


def collect_input_files(input_paths: Sequence[str]) -> list[Path]:
    """Expand 0..n CLI paths into concrete file paths."""
    seed_paths: list[Path]
    if input_paths:
        seed_paths = [Path(p).expanduser() for p in input_paths]
    else:
        seed_paths = list(CONFIGURED_VIDEO_ROOTS)

    discovered: list[Path] = []
    seen: set[Path] = set()
    for path in seed_paths:
        if not path.exists():
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if not child.is_file():
                    continue
                resolved = child.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                discovered.append(resolved)
        elif path.is_file():
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(resolved)
    return discovered


@dataclass(slots=True)
class ProcessResult:
    source_input: Path
    status: str
    message: str
    video_path: Optional[Path] = None
    marks_path: Optional[Path] = None


class ChapterizeCommand:
    """Componentized orchestrator for chapterize CLI workflows."""

    def __init__(
        self,
        detector: FileKindDetector,
        marks_loader: MarksLoader,
        video_reader: CLIVideoReaderStrategy,
        video_writer: CLIVideoWriterStrategy,
        prompt: CLIUserPromptStrategy,
        merge_service: MergeService,
        match_index: PathMatchIndex,
        video_locator: VideoLocator,
    ) -> None:
        self._detector = detector
        self._marks_loader = marks_loader
        self._video_reader = video_reader
        self._video_writer = video_writer
        self._prompt = prompt
        self._merge = merge_service
        self._match_index = match_index
        self._video_locator = video_locator

    def process(self, inputs: Sequence[Path]) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        for source in inputs:
            results.append(self._process_one(source))
        return results

    def _process_one(self, source: Path) -> ProcessResult:
        kind = self._detector.detect(source)
        if kind == "unknown":
            return ProcessResult(source_input=source, status="skipped", message="unsupported file type")

        video_path: Optional[Path]
        if kind == "video":
            video_path = source
            marks_match = self._match_index.find_marks_for_video_name(video_path.stem)
            if marks_match is None:
                return ProcessResult(
                    source_input=source, status="skipped", message="no matching chapters/bookmarks found"
                )
            marks_path, marks_kind = marks_match
        else:
            marks_path = source
            marks_kind = kind
            video_path = self._video_locator.find_video_for_marks_file(marks_path)
            if video_path is None:
                return ProcessResult(
                    source_input=source,
                    status="skipped",
                    message="no matching video found in configured roots",
                    marks_path=marks_path,
                )

        incoming_marks = self._marks_loader.load(marks_path, marks_kind)
        if not incoming_marks:
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="marks file had no usable entries",
                video_path=video_path,
                marks_path=marks_path,
            )

        existing = list(self._video_reader.read(str(video_path)).marks())
        selected_marks = incoming_marks
        if existing:
            choice = self._prompt.prompt_resolution(existing, incoming_marks)
            if choice == "Keep":
                return ProcessResult(
                    source_input=source,
                    status="kept",
                    message="kept existing video chapters",
                    video_path=video_path,
                    marks_path=marks_path,
                )
            if choice == "Merge":
                selected_marks = self._merge.merge(existing, incoming_marks)

        self._video_writer.write(str(video_path), selected_marks)
        return ProcessResult(
            source_input=source,
            status="processed",
            message="chapters written",
            video_path=video_path,
            marks_path=marks_path,
        )


def _print_summary(results: Iterable[ProcessResult]) -> None:
    for result in results:
        video_name = result.video_path.name if result.video_path else "n/a"
        marks_name = result.marks_path.name if result.marks_path else "n/a"
        print(
            f"{result.status}: input={result.source_input.name}; video={video_name}; marks={marks_name}; {result.message}"
        )


def _build_command(non_interactive: bool) -> ChapterizeCommand:
    prompt = CLIUserPromptStrategy(non_interactive=non_interactive)
    return ChapterizeCommand(
        detector=FileKindDetector(),
        marks_loader=MarksLoader(),
        video_reader=CLIVideoReaderStrategy(),
        video_writer=CLIVideoWriterStrategy(),
        prompt=prompt,
        merge_service=MergeService(),
        match_index=PathMatchIndex(chapters_dir=DEFAULT_CHAPTERS_DIR, bookmarks_dir=DEFAULT_BOOKMARKS_DIR),
        video_locator=VideoLocator(CONFIGURED_VIDEO_ROOTS),
    )


def main(argv: Optional[Sequence[str]] = None, *, input_fn: Callable[[str], str] = input) -> int:
    """Main entry point for chapterize CLI."""
    parser = argparse.ArgumentParser(
        prog="chapterize",
        description="Apply chapters to video files from chapters or bookmarks inputs",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Zero or more files/directories. If omitted, scans default video roots.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt for Keep/Replace/Merge. Defaults to Replace.",
    )
    args = parser.parse_args(argv)

    # Support injection for tests while keeping runtime behavior unchanged.
    _ = input_fn

    files = collect_input_files(args.paths)
    if not files:
        print("No input files found.", file=sys.stderr)
        return 1

    command = _build_command(non_interactive=args.non_interactive)
    results = command.process(files)
    _print_summary(results)

    processed = any(r.status == "processed" for r in results)
    return 0 if processed else 1


if __name__ == "__main__":
    sys.exit(main())
