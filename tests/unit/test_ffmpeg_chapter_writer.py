import subprocess
from pathlib import Path

import pytest

from video_file_management.chapterize.chapter_track_writer import ChapterTrackWriter
from video_file_management.chapterize.ffmpeg_writer import FFmpegChapterWriter
from video_file_management.videomarks.models import Chapter, ChaptersFile, TimeCode


def test_generates_ffmetadata_with_chapter_ranges() -> None:
    chapters = ChaptersFile(
        [
            Chapter(TimeCode.from_string("00:00:00.000"), "Opening"),
            Chapter(TimeCode.from_string("00:00:02.500"), "Scene two"),
        ]
    )

    metadata = FFmpegChapterWriter.to_ffmetadata(chapters, duration_ms=10000)

    assert metadata == (
        ";FFMETADATA1\n"
        "\n"
        "[CHAPTER]\n"
        "TIMEBASE=1/1000\n"
        "START=0\n"
        "END=2500\n"
        "title=Opening\n"
        "\n"
        "[CHAPTER]\n"
        "TIMEBASE=1/1000\n"
        "START=2500\n"
        "END=10000\n"
        "title=Scene two\n"
    )


def test_ffmpeg_writer_preserves_container_and_replaces_original_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = tmp_path / "movie.mkv"
    video.write_bytes(b"original")

    def run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        if command[0] == "/usr/bin/ffprobe":
            return subprocess.CompletedProcess(command, 0, stdout="10.0\n", stderr="")
        Path(command[-1]).write_bytes(b"updated")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("video_file_management.chapterize.ffmpeg_writer.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("video_file_management.chapterize.ffmpeg_writer.subprocess.run", run)
    writer = FFmpegChapterWriter()

    writer.write(video, ChaptersFile([Chapter(TimeCode(), "Opening")]))

    assert video.read_bytes() == b"updated"
    assert not video.with_suffix(".mkv.bak").exists()


def test_ffmpeg_writer_preserves_original_on_remux_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    video = tmp_path / "movie.avi"
    video.write_bytes(b"original")

    def run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        if command[0] == "/usr/bin/ffprobe":
            return subprocess.CompletedProcess(command, 0, stdout="10.0\n", stderr="")
        raise subprocess.CalledProcessError(1, command, stderr="remux failed")

    monkeypatch.setattr("video_file_management.chapterize.ffmpeg_writer.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("video_file_management.chapterize.ffmpeg_writer.subprocess.run", run)

    with pytest.raises(RuntimeError, match="FFmpeg"):
        FFmpegChapterWriter().write(video, ChaptersFile([Chapter(TimeCode(), "Opening")]))

    assert video.read_bytes() == b"original"


def test_chapter_track_writer_uses_mp4box_for_mp4_and_ffmpeg_for_other_containers(
    tmp_path: Path,
) -> None:
    class RecordingWriter:
        def __init__(self) -> None:
            self.paths: list[Path] = []

        def write(self, video_path: Path, chapters: ChaptersFile) -> None:
            self.paths.append(video_path)

    mp4box = RecordingWriter()
    ffmpeg = RecordingWriter()
    writer = ChapterTrackWriter(mp4box, ffmpeg)
    chapters = ChaptersFile()

    writer.write(tmp_path / "one.mp4", chapters)
    writer.write(tmp_path / "two.mkv", chapters)

    assert mp4box.paths == [tmp_path / "one.mp4"]
    assert ffmpeg.paths == [tmp_path / "two.mkv"]
