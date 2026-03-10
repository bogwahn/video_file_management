import pytest
from typing import Iterable, List
from video_file_management.chapterize.controller import ChapterizeController
from video_file_management.chapterize.interfaces import (
    UserPromptStrategy, VideoDiscoveryStrategy
)
from video_file_management.marks.models import VideoMark
from video_file_management.marks.protocols import VideoMarksFile
from datetime import timedelta

class MockDiscovery(VideoDiscoveryStrategy):
    def __init__(self, result: str | None = None):
        self._result = result
        self.called_with = None

    def find_video(self, bookmark_path: str) -> str | None:
        self.called_with = bookmark_path
        return self._result

class MockPrompt(UserPromptStrategy):
    def __init__(self, resolution_choice: str = "Merge"):
        self._resolution_choice = resolution_choice
        self.notifications: List[str] = []
        self.errors: List[str] = []
        self.prompted = False

    def prompt_resolution(
        self,
        existing_chapters: Iterable[VideoMark],
        new_chapters: Iterable[VideoMark],
        merged_preview: Iterable[VideoMark],
    ) -> str:
        self.prompted = True
        return self._resolution_choice

    def notify_progress(self, message: str) -> None:
        self.notifications.append(message)

    def notify_error(self, message: str) -> None:
        self.errors.append(message)


class MockMarksFile(VideoMarksFile):
    def __init__(self, path: str, marks: List[VideoMark]):
        self.file_path = path
        self._marks = marks

    def add(self, timecode: str, label: str) -> None: pass
    def remove(self, identifier: str | int) -> None: pass
    def marks(self) -> Iterable[VideoMark]: return self._marks
    def to_string(self) -> str: return ""


class MockReader:
    def __init__(self, marks: List[VideoMark]):
        self._marks = marks
        self.read_path = None

    def read(self, file_path: str) -> VideoMarksFile:
        self.read_path = file_path
        return MockMarksFile(file_path, self._marks)


class MockWriter:
    def __init__(self):
        self.written_path = None
        self.written_marks = None

    def write(self, video_path: str, marks: Iterable[VideoMark]) -> None:
        self.written_path = video_path
        self.written_marks = list(marks)


@pytest.fixture
def base_marks():
    return [
        VideoMark(timedelta(seconds=10), "Chapter 1"),
        VideoMark(timedelta(seconds=20), "Chapter 2"),
    ]

@pytest.fixture
def new_marks():
    return [
        VideoMark(timedelta(seconds=15), "Bookmark A"),
        VideoMark(timedelta(seconds=25), "Bookmark B"),
    ]

def test_controller_aborts_if_video_not_found():
    discovery = MockDiscovery(result=None)
    prompt = MockPrompt()
    controller = ChapterizeController(discovery, prompt, MockReader([]), MockReader([]), MockWriter())
    
    controller.run("dummy.txt")
    
    assert "Video file not found for bookmarks: dummy.txt" in prompt.errors[0]
    assert not prompt.prompted

def test_controller_writes_directly_if_no_existing_chapters(new_marks):
    discovery = MockDiscovery(result="/path/out.mp4")
    prompt = MockPrompt()
    writer = MockWriter()
    
    # Bookmarks has marks, existing has none
    controller = ChapterizeController(discovery, prompt, MockReader(new_marks), MockReader([]), writer)
    
    controller.run("bookmarks.txt")
    
    assert not prompt.prompted  # Should not prompt if no conflict
    assert writer.written_path == "/path/out.mp4"
    assert len(writer.written_marks) == 2

def test_controller_prompts_merge_behavior(base_marks, new_marks):
    discovery = MockDiscovery(result="/path/out.mp4")
    prompt = MockPrompt(resolution_choice="Merge")
    writer = MockWriter()
    
    controller = ChapterizeController(discovery, prompt, MockReader(new_marks), MockReader(base_marks), writer)
    
    controller.run("bookmarks.txt")
    
    assert prompt.prompted
    assert len(writer.written_marks) == 4

def test_controller_aborts_if_keep_chosen(base_marks, new_marks):
    discovery = MockDiscovery(result="/path/out.mp4")
    prompt = MockPrompt(resolution_choice="Keep")
    writer = MockWriter()
    
    controller = ChapterizeController(discovery, prompt, MockReader(new_marks), MockReader(base_marks), writer)
    
    controller.run("bookmarks.txt")
    
    assert prompt.prompted
    assert writer.written_path is None  # Should have skipped writing

def test_controller_replaces_if_replace_chosen(base_marks, new_marks):
    discovery = MockDiscovery(result="/path/out.mp4")
    prompt = MockPrompt(resolution_choice="Replace")
    writer = MockWriter()
    
    controller = ChapterizeController(discovery, prompt, MockReader(new_marks), MockReader(base_marks), writer)
    
    controller.run("bookmarks.txt")
    
    assert prompt.prompted
    assert len(writer.written_marks) == 2
    assert writer.written_marks[0].label == "Bookmark A"
