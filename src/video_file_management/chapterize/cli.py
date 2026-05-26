"""CLI interface for chapterize command."""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable, Optional, Sequence

from ..marks.bookmarks_reader import BookmarksFileReader
from ..marks.chapters_file import ChaptersFile
from ..marks.models import VideoMark
from ..marks.protocols import VideoMarksFile
from ..marks.readers import ChaptersFileReader
from ..marks.writers import MP4ChaptersWriter
from ..metadata_reader import read_file_metadata
from ..remux.service import Remux2Mp4Config, Remux2Mp4Service, RemuxStatus
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
DASH_TRANSLATION = str.maketrans(
    {
        "-": " ",
        "\u2010": " ",
        "\u2011": " ",
        "\u2012": " ",
        "\u2013": " ",
        "\u2014": " ",
        "\u2015": " ",
    }
)
BOOKMARK_SUFFIX_TOKENS = {"bookmark", "bookmarks"}
MIN_TOKEN_OVERLAP = 0.60
MIN_FUZZY_RATIO = 0.86

ENV_VIDEO_ROOTS = "VFM_CHAPTERIZE_VIDEO_ROOTS"
ENV_CHAPTERS_DIR = "VFM_CHAPTERIZE_CHAPTERS_DIR"
ENV_BOOKMARKS_DIR = "VFM_CHAPTERIZE_BOOKMARKS_DIR"


def _prepare_video_for_chapterize(video_path: Path) -> Path:
    if video_path.suffix.lower() != ".mkv":
        return video_path

    service = Remux2Mp4Service()
    results = service.run(
        Remux2Mp4Config(
            input_path=video_path,
            output_path=None,
            recursive=False,
            dry_run=False,
            verbose=False,
            max_workers=1,
        )
    )
    if not results:
        raise RuntimeError("automatic remux to mp4 failed: remux2mp4 returned no result")

    result = results[0]
    if result.status in {RemuxStatus.CONVERTED, RemuxStatus.SKIPPED}:
        return result.output_path

    detail = ", ".join(result.warnings) if result.warnings else result.message
    raise RuntimeError(f"automatic remux to mp4 failed: {detail}")


def _normalize_name(raw: str) -> str:
    return "".join(_normalize_tokens(raw))


def _normalize_tokens(raw: str) -> list[str]:
    lowered = raw.lower().translate(DASH_TRANSLATION)
    tokens = re.findall(r"[a-z0-9]+", lowered)
    while tokens and tokens[-1] in BOOKMARK_SUFFIX_TOKENS:
        tokens.pop()
    if tokens and tokens[-1] in RESOLUTION_TOKENS:
        tokens.pop()
    return tokens


def _token_overlap_score(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    left_set = set(left)
    right_set = set(right)
    common = len(left_set & right_set)
    return common / float(max(len(left_set), len(right_set), 1))


def _fuzzy_ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right).ratio()


_ICLOUD_PATTERN = re.compile(r".+/Mobile Documents/com~apple~CloudDocs")


def _shorten_path(path: Path) -> str:
    """Replace the iCloud Documents root with $CloudDrive in path strings."""
    return _ICLOUD_PATTERN.sub("$CloudDrive", str(path))


def _format_human_elapsed(seconds: float) -> str:
    """Format elapsed seconds as a human-readable duration."""
    if seconds < 60:
        return f"{seconds:.3f}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {secs:.1f}s"
    hours, mins = divmod(minutes, 60)
    return f"{int(hours)}h {int(mins)}m {secs:.0f}s"


def _marks_signature(marks: Iterable[VideoMark]) -> list[tuple[int, str]]:
    signature: list[tuple[int, str]] = []
    for mark in marks:
        total_millis = int(mark.timecode.total_seconds() * 1000)
        label = " ".join(mark.label.lower().split())
        signature.append((total_millis, label))
    signature.sort()
    return signature


def _configured_video_roots() -> tuple[Path, ...]:
    raw = os.getenv(ENV_VIDEO_ROOTS, "")
    if not raw:
        return CONFIGURED_VIDEO_ROOTS
    parsed = tuple(Path(item).expanduser() for item in raw.split(os.pathsep) if item.strip())
    return parsed or CONFIGURED_VIDEO_ROOTS


def _configured_chapters_dir() -> Path:
    raw = os.getenv(ENV_CHAPTERS_DIR, "")
    if not raw:
        return DEFAULT_CHAPTERS_DIR
    return Path(raw).expanduser()


def _configured_bookmarks_dir() -> Path:
    raw = os.getenv(ENV_BOOKMARKS_DIR, "")
    if not raw:
        return DEFAULT_BOOKMARKS_DIR
    return Path(raw).expanduser()


class CLIUserPromptStrategy:
    """Terminal prompt strategy with Keep/Replace/Merge flow."""

    def __init__(self, *, non_interactive: bool = False) -> None:
        self._non_interactive = non_interactive

    def notify_progress(self, message: str) -> None:
        print(message)

    def notify_error(self, message: str) -> None:
        print(f"ERROR: {message}", file=sys.stderr)

    def prompt_resolution(
        self,
        existing: Iterable[VideoMark],
        incoming: Iterable[VideoMark],
        *,
        video_path: Optional[Path] = None,
        marks_path: Optional[Path] = None,
    ) -> str:
        existing_rows = [self._format_mark(mark) for mark in existing]
        incoming_rows = [self._format_mark(mark) for mark in incoming]

        print("\nChapter conflict detected")
        if video_path is not None:
            print(f"Video Path: {video_path.parent} File: {video_path.name}")
        if marks_path is not None:
            print(f"Marks Path: {marks_path.parent} File: {marks_path.name}")
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
        self._chapter_entries = self._build_entries(chapters_dir)
        self._bookmark_entries = self._build_entries(bookmarks_dir)

    def find_marks_for_video_name(
        self, video_stem: str, *, notify_fn: Optional[Callable[[str], None]] = None
    ) -> tuple[Path, str] | None:
        def _notify(label: str, found: bool) -> None:
            if notify_fn:
                status = "Found!" if found else "Not Found"
                notify_fn(f"  method: {label:<26}  {status}")

        key = _normalize_name(video_stem)

        chapter_match = self._pick_best(self._chapters_index.get(key, []))
        if chapter_match is not None:
            _notify("exact match (chapters)", True)
            return chapter_match, "chapters"
        _notify("exact match (chapters)", False)

        chapter_token = self._pick_best_token_overlap(video_stem, self._chapter_entries)
        if chapter_token is not None:
            _notify("token overlap (chapters)", True)
            return chapter_token, "chapters"
        _notify("token overlap (chapters)", False)

        chapter_fuzzy = self._pick_best_fuzzy_ratio(video_stem, self._chapter_entries)
        if chapter_fuzzy is not None:
            _notify("fuzzy logic (chapters)", True)
            return chapter_fuzzy, "chapters"
        _notify("fuzzy logic (chapters)", False)

        bookmark_match = self._pick_best(self._bookmarks_index.get(key, []))
        if bookmark_match is not None:
            _notify("exact match (bookmarks)", True)
            return bookmark_match, "bookmarks"
        _notify("exact match (bookmarks)", False)

        bookmark_token = self._pick_best_token_overlap(video_stem, self._bookmark_entries)
        if bookmark_token is not None:
            _notify("token overlap (bookmarks)", True)
            return bookmark_token, "bookmarks"
        _notify("token overlap (bookmarks)", False)

        bookmark_fuzzy = self._pick_best_fuzzy_ratio(video_stem, self._bookmark_entries)
        if bookmark_fuzzy is not None:
            _notify("fuzzy logic (bookmarks)", True)
            return bookmark_fuzzy, "bookmarks"
        _notify("fuzzy logic (bookmarks)", False)

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

    def _build_entries(self, root: Path) -> list[tuple[str, list[str], Path]]:
        entries: list[tuple[str, list[str], Path]] = []
        if not root.exists() or not root.is_dir():
            return entries
        for path in root.rglob("*.txt"):
            tokens = _normalize_tokens(path.stem)
            normalized = "".join(tokens)
            if not normalized:
                continue
            entries.append((normalized, tokens, path))
        return entries

    def _pick_best_token_overlap(self, target_raw: str, entries: list[tuple[str, list[str], Path]]) -> Optional[Path]:
        target_tokens = _normalize_tokens(target_raw)
        target_normalized = "".join(target_tokens)
        if not target_normalized:
            return None
        winner: tuple[float, float, int, Path] | None = None
        for normalized, tokens, path in entries:
            overlap = _token_overlap_score(target_tokens, tokens)
            if overlap < MIN_TOKEN_OVERLAP:
                continue
            ratio = _fuzzy_ratio(target_normalized, normalized)
            score = (overlap, ratio, -len(path.stem), path)
            if winner is None or score > winner:
                winner = score
        return winner[3] if winner is not None else None

    def _pick_best_fuzzy_ratio(self, target_raw: str, entries: list[tuple[str, list[str], Path]]) -> Optional[Path]:
        target_tokens = _normalize_tokens(target_raw)
        target_normalized = "".join(target_tokens)
        if not target_normalized:
            return None
        winner: tuple[float, float, int, Path] | None = None
        for normalized, tokens, path in entries:
            ratio = _fuzzy_ratio(target_normalized, normalized)
            if ratio < MIN_FUZZY_RATIO:
                continue
            overlap = _token_overlap_score(target_tokens, tokens)
            score = (overlap, ratio, -len(path.stem), path)
            if winner is None or score > winner:
                winner = score
        return winner[3] if winner is not None else None


class VideoLocator:
    """Find videos that correspond to chapters/bookmarks files."""

    def __init__(self, roots: Sequence[Path]) -> None:
        self._roots = roots

    def find_video_for_marks_file(
        self, marks_file: Path, *, notify_fn: Optional[Callable[[str], None]] = None
    ) -> Optional[Path]:
        def _notify(label: str, found: bool) -> None:
            if notify_fn:
                status = "Found!" if found else "Not Found"
                notify_fn(f"  method: {label:<26}  {status}")

        target = _normalize_name(marks_file.stem)
        target_tokens = _normalize_tokens(marks_file.stem)

        candidates: list[tuple[str, list[str], Path]] = []
        for root in self._roots:
            if not root.exists() or not root.is_dir():
                continue
            for candidate in root.rglob("*"):
                if not candidate.is_file() or candidate.suffix.lower() not in VIDEO_EXTENSIONS:
                    continue
                candidates.append((_normalize_name(candidate.stem), _normalize_tokens(candidate.stem), candidate))

        for c_norm, _, path in candidates:
            if c_norm == target:
                _notify("exact match", True)
                return path
        _notify("exact match", False)

        token_best: tuple[float, float, int, Path] | None = None
        for c_norm, c_toks, path in candidates:
            overlap = _token_overlap_score(target_tokens, c_toks)
            if overlap < MIN_TOKEN_OVERLAP:
                continue
            ratio = _fuzzy_ratio(target, c_norm)
            score = (overlap, ratio, -len(path.stem), path)
            if token_best is None or score > token_best:
                token_best = score
        if token_best is not None:
            _notify("token overlap", True)
            return token_best[3]
        _notify("token overlap", False)

        fuzzy_best: tuple[float, float, int, Path] | None = None
        for c_norm, c_toks, path in candidates:
            ratio = _fuzzy_ratio(target, c_norm)
            if ratio < MIN_FUZZY_RATIO:
                continue
            overlap = _token_overlap_score(target_tokens, c_toks)
            score = (overlap, ratio, -len(path.stem), path)
            if fuzzy_best is None or score > fuzzy_best:
                fuzzy_best = score
        if fuzzy_best is not None:
            _notify("fuzzy logic", True)
            return fuzzy_best[3]
        _notify("fuzzy logic", False)

        return None


def collect_input_files(input_paths: Sequence[str]) -> list[Path]:
    """Expand 0..n CLI paths into concrete file paths."""
    seed_paths: list[Path]
    if input_paths:
        seed_paths = [Path(p).expanduser() for p in input_paths]
    else:
        # No paths means "work from here", mirroring `chapterize .`.
        seed_paths = [Path.cwd()]

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
    elapsed_seconds: float = 0.0
    index: int = 0


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
        *,
        force: bool = False,
    ) -> None:
        self._detector = detector
        self._marks_loader = marks_loader
        self._video_reader = video_reader
        self._video_writer = video_writer
        self._prompt = prompt
        self._merge = merge_service
        self._match_index = match_index
        self._video_locator = video_locator
        self._force = force

    def process(self, inputs: Sequence[Path]) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        total = len(inputs)
        for index, source in enumerate(inputs, start=1):
            started = perf_counter()
            result = self._process_one(source, index=index, total=total)
            result.elapsed_seconds = perf_counter() - started
            result.index = index
            results.append(result)
        return results

    def _emit_progress(self, message: str) -> None:
        notify = getattr(self._prompt, "notify_progress", None)
        if callable(notify):
            notify(message)

    def _process_one(self, source: Path, *, index: int = 0, total: int = 0) -> ProcessResult:
        kind = self._detector.detect(source)
        if kind == "unknown":
            return ProcessResult(source_input=source, status="skipped", message="unsupported file type")

        def _notify(msg: str) -> None:
            self._emit_progress(msg)

        video_path: Optional[Path]
        if kind == "video":
            video_path = source
            self._emit_progress(f"searching {index}/{total}: {source.name}")
            marks_match = self._match_index.find_marks_for_video_name(video_path.stem, notify_fn=_notify)
            if marks_match is None:
                return ProcessResult(
                    source_input=source, status="skipped", message="no matching chapters/bookmarks found"
                )
            marks_path, marks_kind = marks_match
        else:
            marks_path = source
            marks_kind = kind
            self._emit_progress(f"searching {index}/{total}: {source.name}")
            video_path = self._video_locator.find_video_for_marks_file(marks_path, notify_fn=_notify)
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

        try:
            if video_path is not None and video_path.suffix.lower() == ".mkv":
                self._emit_progress(f"remuxing {video_path.name} to mp4 before chapter write")
            video_path = _prepare_video_for_chapterize(video_path)
        except Exception as exc:
            return ProcessResult(
                source_input=source,
                status="failed",
                message=str(exc),
                video_path=video_path,
                marks_path=marks_path,
            )

        existing = list(self._video_reader.read(str(video_path)).marks())

        if existing and not self._force and len(existing) >= 3:
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="video already has 3+ chapters; use --force to override",
                video_path=video_path,
                marks_path=marks_path,
            )

        if existing and not self._force and _marks_signature(existing) == _marks_signature(incoming_marks):
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="incoming marks already match existing chapters; use --force to override",
                video_path=video_path,
                marks_path=marks_path,
            )

        selected_marks = incoming_marks
        if existing:
            choice = self._prompt.prompt_resolution(
                existing,
                incoming_marks,
                video_path=video_path,
                marks_path=marks_path,
            )
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

        try:
            self._video_writer.write(str(video_path), selected_marks)
        except Exception as exc:
            return ProcessResult(
                source_input=source,
                status="failed",
                message=f"chapter write failed: {exc}",
                video_path=video_path,
                marks_path=marks_path,
            )

        return ProcessResult(
            source_input=source,
            status="processed",
            message="chapters written and verified",
            video_path=video_path,
            marks_path=marks_path,
        )


def _print_summary(results: Iterable[ProcessResult]) -> None:
    for result in results:
        if result.video_path is not None:
            header_name = result.video_path.name
        elif result.marks_path is not None:
            header_name = result.marks_path.name
        else:
            header_name = result.source_input.name
        print(f" {result.index}. {header_name}")
        if result.video_path is not None:
            print(f"  video_path: {_shorten_path(result.video_path.parent)}")
        else:
            print("  video_path: n/a")
        if result.marks_path is not None:
            print(f"  marks_path: {_shorten_path(result.marks_path.parent)}")
            print(f"  marks_file: {result.marks_path.name}")
        else:
            print("  marks_path: n/a")
            print("  marks_file: n/a")
        print(f"  {result.status}: {result.message}")
        print(f"  elapsed: {_format_human_elapsed(result.elapsed_seconds)}")
        print()


def _print_footer(results: Sequence[ProcessResult], total_elapsed_seconds: float) -> None:
    processed = sum(1 for r in results if r.status == "processed")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")
    kept = sum(1 for r in results if r.status == "kept")
    print(
        "summary: "
        f"processed={processed}; failed={failed}; skipped={skipped}; kept={kept}; "
        f"total elapsed {_format_human_elapsed(total_elapsed_seconds)}"
    )


def _build_command(non_interactive: bool, force: bool) -> ChapterizeCommand:
    prompt = CLIUserPromptStrategy(non_interactive=non_interactive)
    return ChapterizeCommand(
        detector=FileKindDetector(),
        marks_loader=MarksLoader(),
        video_reader=CLIVideoReaderStrategy(),
        video_writer=CLIVideoWriterStrategy(),
        prompt=prompt,
        merge_service=MergeService(),
        match_index=PathMatchIndex(chapters_dir=_configured_chapters_dir(), bookmarks_dir=_configured_bookmarks_dir()),
        video_locator=VideoLocator(_configured_video_roots()),
        force=force,
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
        help="Zero or more files/directories. If omitted, scans the current directory.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt for Keep/Replace/Merge. Defaults to Replace.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force processing even when chapters already match or file already has 3+ chapters.",
    )
    args = parser.parse_args(argv)

    if args.non_interactive and args.force:
        parser.error("--non-interactive and --force cannot be used together")

    # Support injection for tests while keeping runtime behavior unchanged.
    _ = input_fn

    print("Discovering input files...")
    files = collect_input_files(args.paths)
    print(f"Discovered {len(files)} input file(s).")
    if not files:
        print("No input files found.", file=sys.stderr)
        return 1

    command = _build_command(non_interactive=args.non_interactive, force=args.force)
    total_started = perf_counter()
    results = command.process(files)
    total_elapsed = perf_counter() - total_started
    _print_summary(results)
    _print_footer(results, total_elapsed)

    processed = any(r.status == "processed" for r in results)
    return 0 if processed else 1


if __name__ == "__main__":
    sys.exit(main())
