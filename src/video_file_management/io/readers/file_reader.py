from __future__ import annotations

from typing import Protocol, TypeVar

T = TypeVar("T", covariant=True)


class FileReader(Protocol[T]):
    """Protocol for reading mark files."""

    def read(self, file_path: str) -> T:
        """Read marks from a file and return a container."""
        ...
