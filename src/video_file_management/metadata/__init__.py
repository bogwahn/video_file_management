"""File metadata models and protocols."""

from .file_metadata import AudioStreamInfo, FileMetadata, VideoStreamInfo
from .reader import FileMetadataReader
from .video_metadata import ChapterMetadata, VideoFileMetadata
from .writer import FileMetadataWriter

__all__ = [
    "FileMetadata",
    "VideoFileMetadata",
    "AudioStreamInfo",
    "VideoStreamInfo",
    "ChapterMetadata",
    "FileMetadataReader",
    "FileMetadataWriter",
]
