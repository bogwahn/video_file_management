import subprocess
from pathlib import Path

import pytest
from video_file_management.chapterize.mp4box_writer import MP4BoxChapterWriter

from video_file_management.videomarks.models import Chapter, ChaptersFile, TimeCode


def test_generates_nero_chapter_text() -> None:
    writer = MP4BoxChapterWriter()
    chapters = ChaptersFile(
        [
            Chapter(TimeCode.from_string("00:00:01.250"), "Opening"),
            Chapter(TimeCode.from_string("00:01:02.000"), "Scene two"),
        ]
    )

    assert writer.to_nero_text(chapters) == (
        "CHAPTER01=00:00:01.250\nCHAPTER01NAME=Opening\nCHAPTER02=00:01:02.000\nCHAPTER02NAME=Scene two\n"
    )


def test_writer_replaces_original_only_after_mp4box_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = tmp_path / "movie.mp4"
    video.write_bytes(b"original")
    writer = MP4BoxChapterWriter()
    monkeypatch.setattr("video_file_management.chapterize.mp4box_writer.shutil.which", lambda _: "/usr/bin/MP4Box")

    def run(command: list[str], *, check: bool, capture_output: bool) -> subprocess.CompletedProcess[bytes]:
        output_path = Path(command[command.index("-new") + 1])
        output_path.write_bytes(b"updated")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("video_file_management.chapterize.mp4box_writer.subprocess.run", run)

    writer.write(video, ChaptersFile([Chapter(TimeCode(), "Opening")]))

    assert video.read_bytes() == b"updated"
    assert not video.with_suffix(".mp4.bak").exists()


def test_writer_preserves_original_and_raises_when_mp4box_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = tmp_path / "movie.mp4"
    video.write_bytes(b"original")
    writer = MP4BoxChapterWriter()
    monkeypatch.setattr("video_file_management.chapterize.mp4box_writer.shutil.which", lambda _: "/usr/bin/MP4Box")
    monkeypatch.setattr(
        "video_file_management.chapterize.mp4box_writer.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(1, args[0])),
    )

    with pytest.raises(RuntimeError, match="MP4Box"):
        writer.write(video, ChaptersFile([Chapter(TimeCode(), "Opening")]))

    assert video.read_bytes() == b"original"


def test_writer_reports_missing_mp4box(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = tmp_path / "movie.mp4"
    video.write_bytes(b"original")
    monkeypatch.setattr("video_file_management.chapterize.mp4box_writer.shutil.which", lambda _: None)

    with pytest.raises(FileNotFoundError, match="MP4Box"):
        MP4BoxChapterWriter().write(video, ChaptersFile([Chapter(TimeCode(), "Opening")]))
