from pathlib import Path

import pytest

from video_file_management.chapterize import cli


def test_main_uses_configured_icloud_root_and_optional_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, object, str | None]] = []

    class RecordingService:
        def __init__(self, icloud_root: str | Path, writer: object) -> None:
            calls.append((Path(icloud_root), writer, None))

        def chapterize(self, input_path: str | None = None) -> None:
            root, writer, _ = calls[-1]
            calls[-1] = root, writer, input_path

    writer = object()
    monkeypatch.setenv("icloud", "/configured/icloud")
    monkeypatch.setattr(cli, "ChapterTrackWriter", lambda: writer)
    monkeypatch.setattr(cli, "ChapterizeService", RecordingService)

    result = cli.main(["/videos/movie.mp4"])

    assert result == 0
    assert calls == [(Path("/configured/icloud"), writer, "/videos/movie.mp4")]


def test_main_without_target_processes_current_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    targets: list[str | None] = []

    class RecordingService:
        def __init__(self, icloud_root: str | Path, writer: object) -> None:
            pass

        def chapterize(self, input_path: str | None = None) -> None:
            targets.append(input_path)

    monkeypatch.setenv("icloud", "/configured/icloud")
    monkeypatch.setattr(cli, "ChapterTrackWriter", object)
    monkeypatch.setattr(cli, "ChapterizeService", RecordingService)

    result = cli.main([])

    assert result == 0
    assert targets == [None]


def test_main_reports_missing_icloud_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("icloud", raising=False)

    with pytest.raises(SystemExit) as error:
        cli.main([])

    assert error.value.code == 2
    assert "icloud" in capsys.readouterr().err
