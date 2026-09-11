"""Unit tests for InventoryRepository SQLite impl."""

from pathlib import Path

import pytest

from video_file_management.zephyr.inventory import (
    InventoryRecord,
    SqliteInventoryRepository,
)


def test_upsert_and_get(tmp_path: Path) -> None:
    repo = SqliteInventoryRepository(tmp_path / "inv.sqlite3")
    rec = InventoryRecord(
        full_path="/Volumes/ZetcOld/Uncategorized/Jane.Doe.Studio.Title.4k.mp4",
        filename="Jane.Doe.Studio.Title.4k.mp4",
        source_url="https://example.com/scene",
        metadata={"tags": ["new"]},
        star_rating=3.5,
        comments="solid",
    )
    saved = repo.upsert(rec)
    assert saved.id is not None
    got = repo.get_by_path(rec.full_path)
    assert got is not None
    assert got.filename == rec.filename
    assert got.source_url == rec.source_url
    assert got.star_rating == 3.5
    assert got.comments == "solid"
    assert got.metadata["tags"] == ["new"]
    assert got.created_at
    repo.close()


def test_upsert_preserves_created_at(tmp_path: Path) -> None:
    repo = SqliteInventoryRepository(tmp_path / "inv.sqlite3")
    path = "/Volumes/Zetc/VR/Jane.Doe/Jane.Doe.Studio.Title.4k.VR.mp4"
    first = repo.upsert(
        InventoryRecord(full_path=path, filename=Path(path).name, source_url="http://a")
    )
    created = first.created_at
    second = repo.upsert(
        InventoryRecord(
            full_path=path,
            filename=Path(path).name,
            source_url="http://b",
            comments="updated",
        )
    )
    assert second.created_at == created
    assert second.source_url == "http://b"
    assert second.comments == "updated"
    repo.close()


def test_invalid_star_rating_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        InventoryRecord(
            full_path="/x/a.mp4",
            filename="a.mp4",
            star_rating=2.25,
        )


def test_list_all(tmp_path: Path) -> None:
    repo = SqliteInventoryRepository(tmp_path / "inv.sqlite3")
    repo.upsert(InventoryRecord(full_path="/a/one.mp4", filename="one.mp4"))
    repo.upsert(InventoryRecord(full_path="/a/two.mp4", filename="two.mp4"))
    assert len(repo.list_all()) == 2
    repo.close()
