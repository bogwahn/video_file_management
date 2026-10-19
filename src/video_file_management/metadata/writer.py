from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .file_metadata import FileMetadata


class FileMetadataWriter(ABC):
    """Abstract base for writing file metadata."""

    @abstractmethod
    def write(self, path: Path, metadata: FileMetadata) -> None:
        """Write metadata to a file."""
        ...
