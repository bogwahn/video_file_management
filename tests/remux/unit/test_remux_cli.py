from pathlib import Path

from video_file_management.remux import cli as remux
from video_file_management.remux.service import RemuxResult, RemuxStatus


def test_cli_version(capsys) -> None:
    assert remux.main(["--version"]) == 0
    out = capsys.readouterr().out
    assert "remux version" in out


def test_cli_handles_no_files(monkeypatch, capsys) -> None:
    class StubService:
        def run(self, config):
            raise ValueError("No remuxable files found.")

    monkeypatch.setattr(remux, "build_service", lambda: StubService())
    assert remux.main([]) == 1
    out = capsys.readouterr().out
    assert "No remuxable files found" in out


def test_cli_success(monkeypatch, capsys) -> None:
    result = RemuxResult(
        input_path=Path("a.mkv"),
        output_path=Path("a.mp4"),
        status=RemuxStatus.CONVERTED,
        message="converted",
    )

    class StubService:
        def run(self, config):
            return [result]

    monkeypatch.setattr(remux, "build_service", lambda: StubService())
    assert remux.main(["."]) == 0
    out = capsys.readouterr().out
    assert "OK: a.mkv" in out


def test_cli_failure(monkeypatch, capsys) -> None:
    result = RemuxResult(
        input_path=Path("a.mkv"),
        output_path=Path("a.mp4"),
        status=RemuxStatus.FAILED,
        message="ffmpeg failed",
    )

    class StubService:
        def run(self, config):
            return [result]

    monkeypatch.setattr(remux, "build_service", lambda: StubService())
    assert remux.main(["."]) == 1
    out = capsys.readouterr().out
    assert "FAIL: a.mkv" in out
