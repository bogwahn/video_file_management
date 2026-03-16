import json
import os
from pathlib import Path

from video_file_management.remux.remux2mp4 import (
    CommandRunner,
    FfmpegCommandBuilder,
    InputCollector,
    Mp4CompatibilityPolicy,
    OutputPlanner,
    Remux2Mp4Config,
    Remux2Mp4Service,
    RemuxJob,
    RemuxPlanner,
    RemuxStatus,
    RunResult,
    StreamInfo,
    StreamProbe,
)


class FakeRunner(CommandRunner):
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self._returncode = returncode
        self.last_args: list[str] | None = None
        self.last_timeout: int | None = None

    def run(self, args, *, capture_output: bool = True, timeout=None) -> RunResult:
        self.last_args = list(args)
        self.last_timeout = timeout
        return RunResult(stdout=self._stdout, stderr=self._stderr, returncode=self._returncode)


def test_collect_input_files(tmp_path: Path) -> None:
    (tmp_path / "a.mkv").write_text("x")
    (tmp_path / "c.mpg").write_text("y")
    (tmp_path / "d.f4v").write_text("w")
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "b.mkv").write_text("z")
    (sub / "e.f4v").write_text("q")

    collector = InputCollector()
    shallow = collector.collect(tmp_path, recursive=False)
    recursive = collector.collect(tmp_path, recursive=True)

    assert sorted(p.name for p in shallow) == ["a.mkv", "c.mpg", "d.f4v"]
    assert sorted(p.name for p in recursive) == ["a.mkv", "b.mkv", "c.mpg", "d.f4v", "e.f4v"]


def test_collect_rejects_non_mkv(tmp_path: Path) -> None:
    path = tmp_path / "video.mp4"
    path.write_text("x")
    collector = InputCollector()
    try:
        collector.collect(path, recursive=False)
        assert False, "Expected ValueError for unsupported input"
    except ValueError as exc:
        assert "not a supported remux source" in str(exc)


def test_output_planner_paths(tmp_path: Path) -> None:
    input_file = tmp_path / "video.mkv"
    input_file.write_text("x")
    planner = OutputPlanner()

    assert planner.build_output_path(input_file, None) == tmp_path / "video.mp4"

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    assert planner.build_output_path(input_file, out_dir) == out_dir / "video.mp4"

    out_file = tmp_path / "custom.mp4"
    assert planner.build_output_path(input_file, out_file) == out_file


def test_stream_probe_parses_json(tmp_path: Path) -> None:
    payload = {
        "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264"},
            {"index": 1, "codec_type": "audio", "codec_name": "aac"},
        ]
    }
    runner = FakeRunner(stdout=json.dumps(payload))
    probe = StreamProbe(runner=runner)

    streams = probe.probe(tmp_path / "video.mkv")
    assert streams == (
        StreamInfo(index=0, codec_type="video", codec_name="h264"),
        StreamInfo(index=1, codec_type="audio", codec_name="aac"),
    )
    assert runner.last_timeout == 30


def test_executor_reports_timeout_as_failed(tmp_path: Path) -> None:
    from video_file_management.remux.remux2mp4 import RemuxExecutor

    runner = FakeRunner(returncode=124, stderr="command timed out after 900s")
    executor = RemuxExecutor(runner=runner)
    job = RemuxJob(
        input_path=tmp_path / "in.f4v",
        output_path=tmp_path / "out.mp4",
        compatible=True,
        warnings=(),
    )

    result = executor.remux(job, dry_run=False, verbose=False, log_file=None)

    assert result.status == RemuxStatus.FAILED
    assert "timed out" in result.message
    assert runner.last_timeout == 900


def test_compatibility_policy_reports_incompatible() -> None:
    policy = Mp4CompatibilityPolicy()
    streams = [
        StreamInfo(index=0, codec_type="video", codec_name="vp9"),
        StreamInfo(index=1, codec_type="audio", codec_name="aac"),
    ]
    report = policy.check(Path("video.mkv"), streams)
    warnings = report.warning_messages()
    assert warnings
    assert "vp9" in warnings[0]


def test_mpg_policy_requires_h264_aac() -> None:
    policy = Mp4CompatibilityPolicy()
    streams = [
        StreamInfo(index=0, codec_type="video", codec_name="mpeg4"),
        StreamInfo(index=1, codec_type="audio", codec_name="aac"),
    ]
    report = policy.check(Path("video.mpg"), streams)
    warnings = report.warning_messages()
    assert warnings
    assert "mpeg4" in warnings[0]


def test_ffmpeg_command_builder() -> None:
    job = RemuxJob(
        input_path=Path("/in.mkv"),
        output_path=Path("/out.mp4"),
        compatible=True,
        warnings=(),
    )
    builder = FfmpegCommandBuilder()
    cmd = builder.build(job, verbose=False)
    assert cmd[:5] == ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    assert "-c:s" in cmd
    assert "mov_text" in cmd


def test_service_skips_newer_outputs(tmp_path: Path) -> None:
    input_file = tmp_path / "video.mkv"
    output_file = tmp_path / "video.mp4"
    input_file.write_text("x")
    output_file.write_text("y")
    os.utime(output_file, (input_file.stat().st_mtime + 10, input_file.stat().st_mtime + 10))

    class SpyPlanner(RemuxPlanner):
        def __init__(self) -> None:
            super().__init__()
            self.called = False

        def plan(self, input_file: Path, output_path: Path):
            self.called = True
            return super().plan(input_file, output_path)

    planner = SpyPlanner()
    service = Remux2Mp4Service(
        collector=InputCollector(),
        output_planner=OutputPlanner(),
        planner=planner,
    )
    config = Remux2Mp4Config(input_path=tmp_path, recursive=False, max_workers=1)
    results = service.run(config)

    assert results
    assert results[0].status == RemuxStatus.SKIPPED
    assert planner.called is False


def test_service_records_incompatible(tmp_path: Path) -> None:
    input_file = tmp_path / "video.mkv"
    input_file.write_text("x")

    class StubPlanner(RemuxPlanner):
        def plan(self, input_file: Path, output_path: Path):
            return RemuxJob(
                input_path=input_file,
                output_path=output_path,
                compatible=False,
                warnings=("incompatible codec(s): video:vp9",),
            )

    service = Remux2Mp4Service(
        collector=InputCollector(),
        output_planner=OutputPlanner(),
        planner=StubPlanner(),
    )
    config = Remux2Mp4Config(input_path=tmp_path, recursive=False, max_workers=1)
    results = service.run(config)

    assert results
    assert results[0].status == RemuxStatus.INCOMPATIBLE
