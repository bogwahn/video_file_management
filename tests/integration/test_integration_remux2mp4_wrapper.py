from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "scripts" / "remux2mp4"


def _require_tool(name: str) -> None:
    if shutil.which(name) is None:
        pytest.skip(f"{name} not available")


def _make_sample_mkv(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-y",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def test_wrapper_remux_single_file_end_to_end(tmp_path: Path) -> None:
    _require_tool("ffmpeg")
    _require_tool("ffprobe")

    source = tmp_path / "sample.mkv"
    target = tmp_path / "sample.mp4"
    _make_sample_mkv(source)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    result = subprocess.run(
        [str(WRAPPER), str(source)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, f"wrapper failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert target.exists(), "expected MP4 output to be created"
    assert target.stat().st_size > 1024, "output MP4 appears empty"
