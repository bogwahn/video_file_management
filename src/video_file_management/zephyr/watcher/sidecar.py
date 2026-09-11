"""Optional .zephyr.json sidecar next to hot-folder media."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def sidecar_path_for(media_path: Path) -> Path:
    return media_path.with_name(media_path.name + ".zephyr.json")


def load_sidecar(media_path: Path) -> dict[str, Any] | None:
    path = sidecar_path_for(media_path)
    if not path.is_file():
        # Also accept same-stem .zephyr.json (without media ext in the middle)
        alt = media_path.with_suffix(".zephyr.json")
        if alt.is_file():
            path = alt
        else:
            return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
