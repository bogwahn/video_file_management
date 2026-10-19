"""Utility functions for chapterize command."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ...marks.models import VideoMark
from ..remux.service import Remux2Mp4Config, Remux2Mp4Service, RemuxStatus


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


def print_summary(results: Iterable) -> None:
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


def print_footer(results: Iterable, total_elapsed_seconds: float) -> None:
    results_list = list(results)
    processed = sum(1 for r in results_list if r.status == "processed")
    failed = sum(1 for r in results_list if r.status == "failed")
    skipped = sum(1 for r in results_list if r.status == "skipped")
    kept = sum(1 for r in results_list if r.status == "kept")
    print(
        "summary: "
        f"processed={processed}; failed={failed}; skipped={skipped}; kept={kept}; "
        f"total elapsed {_format_human_elapsed(total_elapsed_seconds)}"
    )
