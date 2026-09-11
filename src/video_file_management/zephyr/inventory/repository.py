"""InventoryRepository interface — callers never import SQLite directly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from video_file_management.zephyr.inventory.models import InventoryRecord


class InventoryRepository(ABC):
    """Swappable inventory access for the download-core spike."""

    @abstractmethod
    def upsert(self, record: InventoryRecord) -> InventoryRecord:
        """Insert or update by full_path; preserve created_at on update."""

    @abstractmethod
    def get_by_path(self, full_path: str) -> InventoryRecord | None:
        ...

    @abstractmethod
    def list_all(self, *, limit: int = 1000) -> Sequence[InventoryRecord]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...
