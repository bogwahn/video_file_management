import importlib
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from video_file_management.marks.models import VideoMark

cli = importlib.import_module("video_file_management.chapterize.cli")
FileKindDetector = cli.FileKindDetector
MergeService = cli.MergeService
PathMatchIndex = cli.PathMatchIndex
ChapterizeCommand = cli.ChapterizeCommand
VideoLocator = cli.VideoLocator
CLIUserPromptStrategy = cli.CLIUserPromptStrategy
ProcessResult = cli.ProcessResult


def test_merge_service_dedupes_by_timecode_only() -> None:
    existing = [
        VideoMark(timecode=timedelta(seconds=5), label="Existing Intro"),
        VideoMark(timecode=timedelta(seconds=20), label="Existing Scene"),
    ]
    incoming = [
        VideoMark(timecode=timedelta(seconds=5), label="New Intro Name"),
        VideoMark(timecode=timedelta(seconds=30), label="New Outro"),
    ]

    merged = MergeService().merge(existing, incoming)

    assert [m.label for m in merged] == [
        "Existing Intro",
        "Existing Scene",
        "New Outro",
    ]


def test_file_kind_detector_distinguishes_bookmarks_and_chapters(tmp_path: Path) -> None:
    bookmarks = tmp_path / "clip-bookmarks.txt"
    bookmarks.write_text("0:00:01.000,Intro\n", encoding="utf-8")

    chapters = tmp_path / "clip.txt"
    chapters.write_text("[00:00:01.000] Intro\n", encoding="utf-8")

    detector = FileKindDetector()

    assert detector.detect(bookmarks) == "bookmarks"
    assert detector.detect(chapters) == "chapters"


def test_path_match_index_prefers_chapters_over_bookmarks(tmp_path: Path) -> None:
    chapters_dir = tmp_path / "Chapters"
    bookmarks_dir = tmp_path / "Bookmarks"
    chapters_dir.mkdir()
    bookmarks_dir.mkdir()

    chapters_file = chapters_dir / "Movie.Name.txt"
    chapters_file.write_text("[00:00:01.000] Intro\n", encoding="utf-8")

    bookmarks_file = bookmarks_dir / "Movie.Name-bookmarks.txt"
    bookmarks_file.write_text("0:00:01.000,Intro\n", encoding="utf-8")

    index = PathMatchIndex(chapters_dir=chapters_dir, bookmarks_dir=bookmarks_dir)

    match = index.find_marks_for_video_name("Movie.Name")

    assert match is not None
    assert match[0] == chapters_file
    assert match[1] == "chapters"


def test_video_locator_searches_recursively_only_within_allowed_roots(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    disallowed_root = tmp_path / "disallowed"
    allowed_root.mkdir()
    disallowed_root.mkdir()

    nested_allowed = allowed_root / "x" / "y"
    nested_allowed.mkdir(parents=True)

    allowed_video = nested_allowed / "Movie.Name.mp4"
    allowed_video.write_text("video", encoding="utf-8")

    disallowed_video = disallowed_root / "Movie.Name.mp4"
    disallowed_video.write_text("video", encoding="utf-8")

    locator = VideoLocator([allowed_root])
    marks_file = tmp_path / "Movie.Name-bookmarks.txt"

    found = locator.find_video_for_marks_file(marks_file)

    assert found == allowed_video
    assert found != disallowed_video


def test_prompt_strategy_renders_two_column_preview() -> None:
    prompt = CLIUserPromptStrategy(non_interactive=True)
    output = prompt._render_two_columns(
        "Text",
        ["00:00:01.000 Intro"],
        "Video",
        ["00:00:05.000 Existing"],
    )

    assert "Text" in output
    assert "Video" in output
    assert "00:00:01.000 Intro" in output
    assert "00:00:05.000 Existing" in output


class _FakeDetector:
    def __init__(self, mapping: dict[Path, str]) -> None:
        self._mapping = mapping

    def detect(self, path: Path) -> str:
        return self._mapping.get(path, "unknown")


class _FakeMarksLoader:
    def __init__(self, marks: list[VideoMark]) -> None:
        self._marks = marks

    def load(self, path: Path, kind: str) -> list[VideoMark]:
        _ = path
        _ = kind
        return self._marks


class _FakeVideoReader:
    def __init__(self, existing: list[VideoMark]) -> None:
        self._existing = existing

    class _Marks:
        def __init__(self, marks: list[VideoMark]) -> None:
            self._marks = marks

        def marks(self) -> Iterable[VideoMark]:
            return self._marks

    def read(self, file_path: str):
        _ = file_path
        return self._Marks(self._existing)


class _FakeWriter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[VideoMark]]] = []

    def write(self, video_path: str, marks: Iterable[VideoMark]) -> None:
        self.calls.append((video_path, list(marks)))


class _FakePrompt:
    def __init__(self, response: str) -> None:
        self.response = response

    def prompt_resolution(self, existing: Iterable[VideoMark], incoming: Iterable[VideoMark]) -> str:
        _ = list(existing)
        _ = list(incoming)
        return self.response


class _FakeMatchIndex:
    def __init__(self, match: tuple[Path, str] | None) -> None:
        self._match = match

    def find_marks_for_video_name(self, video_stem: str) -> tuple[Path, str] | None:
        _ = video_stem
        return self._match


class _FakeVideoLocator:
    def __init__(self, video: Path | None) -> None:
        self._video = video

    def find_video_for_marks_file(self, marks_file: Path) -> Path | None:
        _ = marks_file
        return self._video


def test_command_merges_and_writes_for_video_input(tmp_path: Path) -> None:
    video = tmp_path / "Movie.mp4"
    marks_path = tmp_path / "Movie.txt"
    video.write_text("v", encoding="utf-8")
    marks_path.write_text("[00:00:10.000] New\n", encoding="utf-8")

    existing = [VideoMark(timecode=timedelta(seconds=5), label="Existing")]
    incoming = [VideoMark(timecode=timedelta(seconds=10), label="New")]
    writer = _FakeWriter()

    command = ChapterizeCommand(
        detector=_FakeDetector({video: "video"}),
        marks_loader=_FakeMarksLoader(incoming),
        video_reader=_FakeVideoReader(existing),
        video_writer=writer,
        prompt=_FakePrompt("Merge"),
        merge_service=MergeService(),
        match_index=_FakeMatchIndex((marks_path, "chapters")),
        video_locator=_FakeVideoLocator(None),
    )

    results = command.process([video])

    assert len(results) == 1
    assert results[0].status == "processed"
    assert len(writer.calls) == 1
    _, written = writer.calls[0]
    assert [m.label for m in written] == ["Existing", "New"]


def test_command_skips_marks_input_when_video_not_found(tmp_path: Path) -> None:
    marks_file = tmp_path / "Movie-bookmarks.txt"
    marks_file.write_text("0:00:01.000,Intro\n", encoding="utf-8")

    command = ChapterizeCommand(
        detector=_FakeDetector({marks_file: "bookmarks"}),
        marks_loader=_FakeMarksLoader([VideoMark(timecode=timedelta(seconds=1), label="Intro")]),
        video_reader=_FakeVideoReader([]),
        video_writer=_FakeWriter(),
        prompt=_FakePrompt("Replace"),
        merge_service=MergeService(),
        match_index=_FakeMatchIndex(None),
        video_locator=_FakeVideoLocator(None),
    )

    results = command.process([marks_file])

    assert len(results) == 1
    assert results[0].status == "skipped"
    assert "configured roots" in results[0].message
