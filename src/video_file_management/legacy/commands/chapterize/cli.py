"""CLI interface for chapterize command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import perf_counter
from typing import Callable, Optional, Sequence

from .chapterize_command import ChapterizeCommand
from .cli_user_prompt_strategy import CLIUserPromptStrategy
from .cli_video_reader_strategy import CLIVideoReaderStrategy
from .cli_video_writer_strategy import CLIVideoWriterStrategy
from .config import configured_bookmarks_dir, configured_chapters_dir, configured_video_roots
from .file_kind_detector import FileKindDetector
from .marks_loader import MarksLoader
from .merge_service import MergeService
from .path_match_index import PathMatchIndex
from .util import print_footer, print_summary
from .video_locator import VideoLocator


def collect_input_files(input_paths: Sequence[str]) -> list[Path]:
    """Expand 0..n CLI paths into concrete file paths."""
    seed_paths: list[Path]
    if input_paths:
        seed_paths = [Path(p).expanduser() for p in input_paths]
    else:
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


def _build_command(non_interactive: bool, force: bool) -> ChapterizeCommand:
    prompt = CLIUserPromptStrategy(non_interactive=non_interactive)
    return ChapterizeCommand(
        detector=FileKindDetector(),
        marks_loader=MarksLoader(),
        video_reader=CLIVideoReaderStrategy(),
        video_writer=CLIVideoWriterStrategy(),
        prompt=prompt,
        merge_service=MergeService(),
        match_index=PathMatchIndex(chapters_dir=configured_chapters_dir(), bookmarks_dir=configured_bookmarks_dir()),
        video_locator=VideoLocator(configured_video_roots()),
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
    parser.add_argument(
        "-s",
        "--source",
        help="Path to a chapters/bookmarks text file to use as marks source for a single video input (implies force replace).",
    )
    args = parser.parse_args(argv)

    if args.non_interactive and args.force:
        parser.error("--non-interactive and --force cannot be used together")

    explicit_source: Path | None = None
    explicit_video_input: Path | None = None
    if args.source:
        if len(args.paths) != 1:
            parser.error("--source requires exactly one positional input path (a single video file)")
        explicit_video_input = Path(args.paths[0]).expanduser()
        if not explicit_video_input.exists() or not explicit_video_input.is_file():
            parser.error("--source mode requires the positional input to be an existing video file")
        explicit_source = Path(args.source).expanduser()
        if not explicit_source.exists() or not explicit_source.is_file():
            parser.error("--source must point to an existing chapters/bookmarks file")

    effective_force = args.force or (explicit_source is not None)

    _ = input_fn

    print("Discovering input files...")
    files = [explicit_video_input.resolve()] if explicit_video_input is not None else collect_input_files(args.paths)
    print(f"Discovered {len(files)} input file(s).")
    if not files:
        print("No input files found.", file=sys.stderr)
        return 1

    command = _build_command(non_interactive=args.non_interactive, force=effective_force)
    total_started = perf_counter()
    results = command.process(files, marks_source=explicit_source.resolve() if explicit_source else None)
    total_elapsed = perf_counter() - total_started
    print_summary(results)
    print_footer(results, total_elapsed)

    processed = any(r.status == "processed" for r in results)
    return 0 if processed else 1


if __name__ == "__main__":
    sys.exit(main())
