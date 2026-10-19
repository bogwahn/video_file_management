from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .chapter import Chapter
from .resolution import Resolution
from .timecode import TimeCode


class VideoFile:
    """Immutable description of a video file; performs no file I/O.

    The path-derived properties are computed from the path. Metadata properties are supplied by the caller and are
    None when unknown.
    """

    def __init__(
        self,
        file_path: str,
        *,
        resolution: Resolution | None = None,
        finder_tags: Iterable[str] = (),
        container: str | None = None,
        duration: TimeCode | None = None,
        video_codec: str | None = None,
        audio_codec: str | None = None,
        frame_rate: float | None = None,
        bitrate: int | None = None,
        file_size: int | None = None,
        chapters: Iterable[Chapter] = (),
    ) -> None:
        self._path = Path(file_path).expanduser().absolute()
        self._resolution = resolution
        self._finder_tags = tuple(finder_tags)
        self._container = container
        self._duration = duration
        self._video_codec = video_codec
        self._audio_codec = audio_codec
        self._frame_rate = frame_rate
        self._bitrate = bitrate
        self._file_size = file_size
        self._chapters = list(chapters)

    @property
    def Filename(self) -> str:
        return self._path.name

    @property
    def Ext(self) -> str:
        return self._path.suffix

    @property
    def FullPath(self) -> str:
        return str(self._path)

    @property
    def Resolution(self) -> Resolution | None:
        return self._resolution

    @property
    def FinderTags(self) -> tuple[str, ...]:
        return self._finder_tags

    @property
    def Container(self) -> str | None:
        return self._container

    @property
    def Duration(self) -> TimeCode | None:
        return self._duration

    @property
    def VideoCodec(self) -> str | None:
        return self._video_codec

    @property
    def AudioCodec(self) -> str | None:
        return self._audio_codec

    @property
    def FrameRate(self) -> float | None:
        """Frames per second."""
        return self._frame_rate

    @property
    def Bitrate(self) -> int | None:
        """Overall bitrate in bits per second."""
        return self._bitrate

    @property
    def FileSize(self) -> int | None:
        """Size in bytes."""
        return self._file_size

    @property
    def Chapters(self) -> list[Chapter]:
        return list(self._chapters)
