"""Inventory models — locked initial-phase fields only."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

STAR_RATINGS = frozenset({0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0})


def validate_star_rating(value: float | None) -> float | None:
    if value is None:
        return None
    v = float(value)
    if v not in STAR_RATINGS:
        raise ValueError(f"star_rating must be one of {sorted(STAR_RATINGS)}; got {value}")
    return v


@dataclass
class InventoryRecord:
    full_path: str
    filename: str
    source_url: str | None = None
    created_at: str | None = None  # ISO-8601; set on insert if missing
    metadata: dict[str, Any] = field(default_factory=dict)
    star_rating: float | None = None
    comments: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.star_rating = validate_star_rating(self.star_rating)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> InventoryRecord:
        meta = data.get("metadata") or data.get("metadata_json") or {}
        if isinstance(meta, str):
            import json

            meta = json.loads(meta) if meta else {}
        return cls(
            id=data.get("id"),
            full_path=str(data["full_path"]),
            filename=str(data["filename"]),
            source_url=data.get("source_url"),
            created_at=data.get("created_at"),
            metadata=dict(meta),
            star_rating=data.get("star_rating"),
            comments=data.get("comments"),
        )
