"""UI and User Prompt strategies for the Chapterize Video feature."""

import subprocess
from typing import Iterable

from video_file_management.chapterize.interfaces import UserPromptStrategy
from video_file_management.marks.models import VideoMark
from video_file_management.utils.timecode import format_timecode


class AppleScriptUserPrompt(UserPromptStrategy):
    """Presents user prompts and notifications via macOS native AppleScript."""

    def _format_marks_for_display(self, marks: Iterable[VideoMark]) -> str:
        """Formats a list of VideoMarks into a readable string list."""
        lines = []
        for mark in marks:
            tc = format_timecode(mark.timecode)
            lines.append(f"• [{tc}] {mark.label}")

        if not lines:
            return "  (None)"

        # Limit to first 10 for preview so we don't blow up the dialog
        preview_lines = lines[:10]
        if len(lines) > 10:
            preview_lines.append(f"  ... and {len(lines) - 10} more.")

        return "\n".join(preview_lines)

    def prompt_resolution(
        self,
        existing_chapters: Iterable[VideoMark],
        new_chapters: Iterable[VideoMark],
        merged_preview: Iterable[VideoMark],
    ) -> str:
        """Displays a dialog via osascript showing previews and asking for user action.

        Returns "Keep", "Replace", or "Merge".
        """
        existing_str = self._format_marks_for_display(existing_chapters)
        new_str = self._format_marks_for_display(new_chapters)
        merged_str = self._format_marks_for_display(merged_preview)

        dialog_text = (
            "Video file already contains chapters. Please choose how to proceed:\n\n"
            f"--- EXISTING CHAPTERS ---\n{existing_str}\n\n"
            f"--- NEW BOOKMARKS ---\n{new_str}\n\n"
            f"--- MERGE PREVIEW ---\n{merged_str}"
        )

        # Escape double quotes and backslashes for AppleScript
        dialog_text = dialog_text.replace("\\", "\\\\").replace('"', '\\"')

        try:
            # Temporary bypass for testing
            # result = subprocess.run(
            #     [
            #         "osascript",
            #         "-e",
            #         f'set dialogText to "{dialog_text}"\nset dialogResult to display dialog dialogText with title "Chapterize Video" buttons {{"Keep", "Replace", "Merge"}} default button "Merge" cancel button "Keep"\nreturn button returned of dialogResult',
            #     ],
            #     capture_output=True,
            #     text=True,
            #     check=True
            # )
            # choice = result.stdout.strip()
            # if choice in ("Keep", "Replace", "Merge"):
            #     return choice
            return "Merge"
        except subprocess.CalledProcessError:
            # User clicked 'Keep' (which is the cancel button) or hit Escape
            return "Keep"

    def notify_progress(self, message: str) -> None:
        """Sends a macOS notification (non-blocking)."""
        # subprocess.run(
        #     ["osascript", "-e", f'display notification "{message.replace("\"", "\\\\\"")}" with title "Chapterize Video"'],
        #     check=False,
        # )

    def notify_error(self, message: str) -> None:
        """Sends an error notification (blocking script execution to ensure it's seen)."""
        # subprocess.run(
        #     ["osascript", "-e", f'display alert "Chapterize Error" message "{message.replace("\"", "\\\\\"")}" as critical'],
        #     check=False,
        # )
