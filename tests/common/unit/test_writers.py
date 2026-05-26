from types import SimpleNamespace

from video_file_management.marks import writers


def test_verify_written_chapters_rejects_tiny_output(monkeypatch, tmp_path) -> None:
    output = tmp_path / "out.mp4"
    output.write_bytes(b"tiny")

    monkeypatch.setattr(
        writers,
        "read_file_metadata",
        lambda path: SimpleNamespace(video=SimpleNamespace(codec="h264", width=1920, height=1080)),
    )
    monkeypatch.setattr(
        writers,
        "read_chapters",
        lambda path: SimpleNamespace(errors=[], chapters=[object(), object()]),
    )

    verified, error = writers._verify_written_chapters(output, 2)

    assert not verified
    assert error is not None
    assert "unexpectedly small" in error


def test_verify_written_chapters_requires_video_stream(monkeypatch, tmp_path) -> None:
    output = tmp_path / "out.mp4"
    output.write_bytes(b"x" * 4096)

    monkeypatch.setattr(
        writers,
        "read_file_metadata",
        lambda path: SimpleNamespace(video=SimpleNamespace(codec=None, width=None, height=None)),
    )
    monkeypatch.setattr(
        writers,
        "read_chapters",
        lambda path: SimpleNamespace(errors=[], chapters=[object(), object()]),
    )

    verified, error = writers._verify_written_chapters(output, 2)

    assert not verified
    assert error == "No video streams found after chapter write"


def test_verify_written_chapters_accepts_valid_video_with_chapters(monkeypatch, tmp_path) -> None:
    output = tmp_path / "out.mp4"
    output.write_bytes(b"x" * 4096)

    monkeypatch.setattr(
        writers,
        "read_file_metadata",
        lambda path: SimpleNamespace(video=SimpleNamespace(codec="h264", width=1920, height=1080)),
    )
    monkeypatch.setattr(
        writers,
        "read_chapters",
        lambda path: SimpleNamespace(errors=[], chapters=[object(), object()]),
    )

    verified, error = writers._verify_written_chapters(output, 2)

    assert verified
    assert error is None
