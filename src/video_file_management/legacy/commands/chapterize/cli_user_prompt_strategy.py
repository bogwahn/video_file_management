"""User interface and prompting logic."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional, Protocol

from ...marks.models import VideoMark
from ...utils.timecode import format_timecode


class PromptLike(Protocol):
    def prompt_resolution(
        self,
        existing: Iterable[VideoMark],
        incoming: Iterable[VideoMark],
        *,
        video_path: Optional[Path] = None,
        marks_path: Optional[Path] = None,
    ) -> str: ...


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
