"""SQLite concrete InventoryRepository for the spike."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Sequence

from video_file_management.zephyr.inventory.models import InventoryRecord, validate_star_rating
from video_file_management.zephyr.inventory.repository import InventoryRepository

SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
  id              INTEGER PRIMARY KEY,
  full_path       TEXT NOT NULL UNIQUE,
  filename        TEXT NOT NULL,
  source_url      TEXT,
  created_at      TEXT NOT NULL,
  metadata_json   TEXT,
  star_rating     REAL,
  comments        TEXT,
  CHECK (
    star_rating IS NULL OR star_rating IN (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5)
  )
);
"""


class SqliteInventoryRepository(InventoryRepository):
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent and str(self.db_path.parent) not in ("", "."):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def upsert(self, record: InventoryRecord) -> InventoryRecord:
        validate_star_rating(record.star_rating)
        existing = self.get_by_path(record.full_path)
        meta_json = json.dumps(record.metadata or {}, ensure_ascii=False)
        if existing is None:
            cur = self._conn.execute(
                """
                INSERT INTO downloads (
                  full_path, filename, source_url, created_at,
                  metadata_json, star_rating, comments
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.full_path,
                    record.filename,
                    record.source_url,
                    record.created_at,
                    meta_json,
                    record.star_rating,
                    record.comments,
                ),
            )
            self._conn.commit()
            record.id = int(cur.lastrowid)
            return record

        # Preserve first-created timestamp; update other fields.
        self._conn.execute(
            """
            UPDATE downloads SET
              filename = ?,
              source_url = COALESCE(?, source_url),
              metadata_json = ?,
              star_rating = COALESCE(?, star_rating),
              comments = COALESCE(?, comments)
            WHERE full_path = ?
            """,
            (
                record.filename,
                record.source_url,
                meta_json,
                record.star_rating,
                record.comments,
                record.full_path,
            ),
        )
        self._conn.commit()
        updated = self.get_by_path(record.full_path)
        assert updated is not None
        return updated

    def get_by_path(self, full_path: str) -> InventoryRecord | None:
        row = self._conn.execute(
            "SELECT * FROM downloads WHERE full_path = ?", (full_path,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_all(self, *, limit: int = 1000) -> Sequence[InventoryRecord]:
        rows = self._conn.execute(
            "SELECT * FROM downloads ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> InventoryRecord:
        meta_raw = row["metadata_json"]
        meta = json.loads(meta_raw) if meta_raw else {}
        return InventoryRecord(
            id=row["id"],
            full_path=row["full_path"],
            filename=row["filename"],
            source_url=row["source_url"],
            created_at=row["created_at"],
            metadata=meta,
            star_rating=row["star_rating"],
            comments=row["comments"],
        )
