"""Core chapterize command orchestration."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Callable, Optional, Sequence

from ...marks.models import VideoMark
from .cli_user_prompt_strategy import PromptLike
from .cli_video_reader_strategy import VideoReaderLike
from .cli_video_writer_strategy import VideoWriterLike
from .file_kind_detector import FileKindDetectorLike
from .marks_loader import MarksLoaderLike
from .merge_service import MergeServiceLike
from .path_match_index import PathMatchIndexLike
from .process_result import ProcessResult
from .util import _marks_signature, _prepare_video_for_chapterize
from .video_locator import VideoLocatorLike


class ChapterizeCommand:
    """Componentized orchestrator for chapterize CLI workflows."""

    def __init__(
        self,
        detector: FileKindDetectorLike,
        marks_loader: MarksLoaderLike,
        video_reader: VideoReaderLike,
        video_writer: VideoWriterLike,
        prompt: PromptLike,
        merge_service: MergeServiceLike,
        match_index: PathMatchIndexLike,
        video_locator: VideoLocatorLike,
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

    def process(self, inputs: Sequence[Path], *, marks_source: Optional[Path] = None) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        total = len(inputs)
        for index, source in enumerate(inputs, start=1):
            started = perf_counter()
            result = self._process_one(source, index=index, total=total, explicit_marks_path=marks_source)
            result.elapsed_seconds = perf_counter() - started
            result.index = index
            results.append(result)
        return results

    def _emit_progress(self, message: str) -> None:
        notify = getattr(self._prompt, "notify_progress", None)
        if callable(notify):
            notify(message)

    def _process_one(
        self,
        source: Path,
        *,
        index: int = 0,
        total: int = 0,
        explicit_marks_path: Optional[Path] = None,
    ) -> ProcessResult:
        kind = self._detector.detect(source)
        if kind == "unknown":
            return ProcessResult(source_input=source, status="skipped", message="unsupported file type")

        def _notify(msg: str) -> None:
            self._emit_progress(msg)

        if explicit_marks_path is not None:
            resolved = self._resolve_explicit_source(source, explicit_marks_path, index, total, _notify)
        elif kind == "video":
            resolved = self._resolve_video_source(source, index, total, _notify)
        else:
            resolved = self._resolve_marks_source(source, kind, index, total, _notify)

        if isinstance(resolved, ProcessResult):
            return resolved

        video_path, marks_path, marks_kind = resolved
        try:
            incoming_marks = self._marks_loader.load(marks_path, marks_kind)
        except OSError as exc:
            return ProcessResult(
                source_input=source,
                status="failed",
                message=f"could not read marks file: {exc}",
                video_path=video_path,
                marks_path=marks_path,
            )
        if not incoming_marks:
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="marks file had no usable entries",
                video_path=video_path,
                marks_path=marks_path,
            )

        return self._apply_marks_to_video(source, video_path, marks_path, incoming_marks)

    def _resolve_explicit_source(
        self,
        source: Path,
        explicit_marks_path: Path,
        index: int,
        total: int,
        notify_fn: Callable[[str], None],
    ) -> tuple[Path, Path, str] | ProcessResult:
        if self._detector.detect(source) != "video":
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="--source requires the input path to be a video file",
            )

        marks_kind = self._detector.detect(explicit_marks_path)
        if marks_kind not in {"chapters", "bookmarks"}:
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="--source must point to a chapters/bookmarks text file",
                video_path=source,
                marks_path=explicit_marks_path,
            )

        self._emit_progress(f"searching {index}/{total}: {source.name}")
        self._emit_progress("  method: explicit source            Found!")
        return source, explicit_marks_path, marks_kind

    def _resolve_video_source(
        self,
        source: Path,
        index: int,
        total: int,
        notify_fn: Callable[[str], None],
    ) -> tuple[Path, Path, str] | ProcessResult:
        video_path = source
        self._emit_progress(f"searching {index}/{total}: {source.name}")
        marks_match = self._match_index.find_marks_for_video_name(video_path.stem, notify_fn=notify_fn)
        if marks_match is None:
            return ProcessResult(source_input=source, status="skipped", message="no matching chapters/bookmarks found")
        marks_path, marks_kind = marks_match
        return video_path, marks_path, marks_kind

    def _resolve_marks_source(
        self,
        source: Path,
        marks_kind: str,
        index: int,
        total: int,
        notify_fn: Callable[[str], None],
    ) -> tuple[Path, Path, str] | ProcessResult:
        marks_path = source
        self._emit_progress(f"searching {index}/{total}: {source.name}")
        video_path = self._video_locator.find_video_for_marks_file(marks_path, notify_fn=notify_fn)
        if video_path is None:
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="no matching video found in configured roots",
                marks_path=marks_path,
            )
        return video_path, marks_path, marks_kind

    def _apply_marks_to_video(
        self,
        source: Path,
        video_path: Path,
        marks_path: Path,
        incoming_marks: list[VideoMark],
    ) -> ProcessResult:
        try:
            if video_path is not None and video_path.suffix.lower() == ".mkv":
                self._emit_progress(f"remuxing {video_path.name} to mp4 before chapter write")
            prepared_video_path = _prepare_video_for_chapterize(video_path)
        except Exception as exc:
            return ProcessResult(
                source_input=source,
                status="failed",
                message=str(exc),
                video_path=video_path,
                marks_path=marks_path,
            )

        try:
            existing = list(self._video_reader.read(str(prepared_video_path)).marks())
        except OSError as exc:
            return ProcessResult(
                source_input=source,
                status="failed",
                message=f"could not read existing chapters: {exc}",
                video_path=prepared_video_path,
                marks_path=marks_path,
            )

        if existing and not self._force and len(existing) >= 3:
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="video already has 3+ chapters; use --force to override",
                video_path=prepared_video_path,
                marks_path=marks_path,
            )

        if existing and not self._force and _marks_signature(existing) == _marks_signature(incoming_marks):
            return ProcessResult(
                source_input=source,
                status="skipped",
                message="incoming marks already match existing chapters; use --force to override",
                video_path=prepared_video_path,
                marks_path=marks_path,
            )

        selected_marks = incoming_marks
        if existing:
            choice = self._prompt.prompt_resolution(
                existing,
                incoming_marks,
                video_path=prepared_video_path,
                marks_path=marks_path,
            )
            if choice == "Keep":
                return ProcessResult(
                    source_input=source,
                    status="kept",
                    message="kept existing video chapters",
                    video_path=prepared_video_path,
                    marks_path=marks_path,
                )
            if choice == "Merge":
                selected_marks = self._merge.merge(existing, incoming_marks)

        try:
            self._video_writer.write(str(prepared_video_path), selected_marks)
        except Exception as exc:
            return ProcessResult(
                source_input=source,
                status="failed",
                message=f"chapter write failed: {exc}",
                video_path=prepared_video_path,
                marks_path=marks_path,
            )

        return ProcessResult(
            source_input=source,
            status="processed",
            message="chapters written and verified",
            video_path=prepared_video_path,
            marks_path=marks_path,
        )
