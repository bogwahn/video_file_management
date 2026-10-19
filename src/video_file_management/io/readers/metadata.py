from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from ...metadata import AudioStreamInfo, ChapterMetadata, VideoFileMetadata, VideoStreamInfo
from . import tag

# Backwards-compatible aliases for existing code
FileMetadata = VideoFileMetadata


def _parse_fraction(value: str) -> Optional[float]:
    if not value:
        return None
    try:
        if "/" in value:
            num, den = value.split("/", 1)
            num_f = float(num)
            den_f = float(den)
            if den_f == 0:
                return None
            return num_f / den_f
        return float(value)
    except Exception:
        return None


def _run_ffprobe(path: Path) -> Tuple[Optional[dict], Optional[str]]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None, "ffprobe not found in PATH"
    try:
        res = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                "-show_chapters",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"ffprobe error: {exc}"

    try:
        return json.loads(res.stdout or "{}"), None
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"ffprobe parse error: {exc}"


def _parse_video_stream(stream: dict) -> VideoStreamInfo:
    v = VideoStreamInfo()
    try:
        raw_w = stream.get("width")
        v.width = int(raw_w) if raw_w is not None else None
        raw_h = stream.get("height")
        v.height = int(raw_h) if raw_h is not None else None
    except Exception:
        pass
    v.codec = stream.get("codec_name")
    fps_raw = stream.get("r_frame_rate") or stream.get("avg_frame_rate")
    v.fps = _parse_fraction(fps_raw) if isinstance(fps_raw, str) else None
    try:
        bit_raw = stream.get("bits_per_raw_sample") or stream.get("bits_per_sample")
        if bit_raw is not None:
            v.bit_depth = int(bit_raw)
    except Exception:
        pass
    return v


def _parse_audio_stream(stream: dict) -> AudioStreamInfo:
    a = AudioStreamInfo()
    a.codec = stream.get("codec_name")
    try:
        sr = stream.get("sample_rate")
        a.sample_rate = int(sr) if sr is not None else None
    except Exception:
        pass
    try:
        ch = stream.get("channels")
        a.channels = int(ch) if ch is not None else None
    except Exception:
        pass
    return a


def _parse_chapters(data: dict) -> list[ChapterMetadata]:
    """Extract chapter entries from ffprobe data."""
    chapters: list[ChapterMetadata] = []
    for entry in data.get("chapters", []) or []:
        # ffprobe `start` may be timebase ticks for chapters; prefer `start_time`
        # which is normalized to seconds.
        start_raw = entry.get("start_time", entry.get("start", 0.0))
        try:
            start = float(start_raw)
        except Exception:
            start = 0.0
        title = ""
        if isinstance(entry, dict):
            raw_tags = entry.get("tags")
            tags = raw_tags if isinstance(raw_tags, dict) else {}
            title = tags.get("title") or tags.get("TITLE") or entry.get("title") or ""
        chapters.append(ChapterMetadata(start_seconds=start, title=title))
    return chapters


def read_file_metadata(path: Path) -> VideoFileMetadata:
    """Return container, runtime, streams, chapters, and Finder tags in one pass."""
    meta = VideoFileMetadata(path=path)

    data, error = _run_ffprobe(path)
    if error:
        meta.errors.append(error)
        return meta
    if not data:
        meta.errors.append("ffprobe returned no data")
        return meta

    try:
        meta.format_name = data.get("format", {}).get("format_name")
        duration = data.get("format", {}).get("duration")
        if duration is not None:
            meta.runtime_seconds = float(duration)
    except Exception:
        meta.errors.append("format/runtme parse failed")

    streams = data.get("streams", []) or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video_stream:
        meta.video = _parse_video_stream(video_stream)
    if audio_stream:
        meta.audio = _parse_audio_stream(audio_stream)

    try:
        meta.chapters = _parse_chapters(data)
    except Exception:
        meta.errors.append("chapters parse failed")

    try:
        tag_result = tag.read_finder_tags(path)
        meta.tags = tag_result.tags or []
        if tag_result.errors:
            meta.errors.extend(tag_result.errors)
    except Exception:
        meta.errors.append("tag read failed")

    return meta


# Backwards-compatible alias
def read_basic_metadata(path: Path) -> FileMetadata:
    return read_file_metadata(path)
