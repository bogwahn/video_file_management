from __future__ import annotations

from typing import Protocol, TypeVar

T = TypeVar("T", contravariant=True)


class FileWriter(Protocol[T]):
    """Protocol for writing mark files."""

    def write(self, file_path: str, marks: T) -> None:
        """Write marks to a file."""
        ...
