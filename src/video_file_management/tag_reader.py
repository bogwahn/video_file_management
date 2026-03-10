from __future__ import annotations

import plistlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

try:
    import xattr  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    xattr = None


@dataclass(slots=True)
class TagReadResult:
    tags: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def read_finder_tags(path: Path) -> TagReadResult:
    """Return Finder tags stored on `path`, or errors if encountered."""
    result = TagReadResult()
    key = "com.apple.metadata:_kMDItemUserTags"
    try:
        if xattr is not None:
            attrs = xattr.xattr(str(path))
            raw = attrs.get(key, None)
            if raw:
                result.tags = list(plistlib.loads(raw))
            return result
        res = subprocess.run(
            ["xattr", "-px", key, str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return result
        hex_value = res.stdout.strip().replace("\n", "")
        raw = bytes.fromhex(hex_value)
        result.tags = list(plistlib.loads(raw))
        return result
    except Exception as exc:
        result.errors.append(f"tag read error: {exc}")
        return result
