from __future__ import annotations

from pathlib import Path


def replace_source(source: Path, output_video: Path, writer_name: str) -> None:
    if not output_video.is_file() or output_video.stat().st_size == 0:
        raise RuntimeError(f"{writer_name} did not produce a valid output video for {source}")
    output_video.replace(source)
