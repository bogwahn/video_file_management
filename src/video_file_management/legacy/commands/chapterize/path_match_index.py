"""Indexes chapter and bookmark files for quick per-video matching."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional, Protocol

from .config import (
    BOOKMARK_SUFFIX_TOKENS,
    DASH_TRANSLATION,
    MIN_FUZZY_RATIO,
    MIN_TOKEN_OVERLAP,
    RESOLUTION_TOKENS,
)


def _normalize_name(raw: str) -> str:
    return "".join(_normalize_tokens(raw))


def _normalize_tokens(raw: str) -> list[str]:
    lowered = raw.lower().translate(DASH_TRANSLATION)
    tokens = re.findall(r"[a-z0-9]+", lowered)
    while tokens and tokens[-1] in BOOKMARK_SUFFIX_TOKENS:
        tokens.pop()
    if tokens and tokens[-1] in RESOLUTION_TOKENS:
        tokens.pop()
    return tokens


def _token_overlap_score(left: list[str], right: list[str]) -> float:
    if not left or not right:
        return 0.0
    left_set = set(left)
    right_set = set(right)
    common = len(left_set & right_set)
    return common / float(max(len(left_set), len(right_set), 1))


def _fuzzy_ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    import difflib

    return difflib.SequenceMatcher(None, left, right).ratio()


class PathMatchIndexLike(Protocol):
    def find_marks_for_video_name(
        self, video_stem: str, *, notify_fn: Optional[Callable[[str], None]] = None
    ) -> tuple[Path, str] | None: ...


class PathMatchIndex:
    """Indexes chapter and bookmark files for quick per-video matching."""

    def __init__(self, chapters_dir: Path, bookmarks_dir: Path) -> None:
        self._chapters_index = self._build_index(chapters_dir)
        self._bookmarks_index = self._build_index(bookmarks_dir)
        self._chapter_entries = self._build_entries(chapters_dir)
        self._bookmark_entries = self._build_entries(bookmarks_dir)

    def find_marks_for_video_name(
        self, video_stem: str, *, notify_fn: Optional[Callable[[str], None]] = None
    ) -> tuple[Path, str] | None:
        def _notify(label: str, found: bool) -> None:
            if notify_fn:
                status = "Found!" if found else "Not Found"
                notify_fn(f"  method: {label:<26}  {status}")

        key = _normalize_name(video_stem)
        for label, root_index, entries, kind in (
            ("exact match (chapters)", self._chapters_index, self._chapter_entries, "chapters"),
            ("exact match (bookmarks)", self._bookmarks_index, self._bookmark_entries, "bookmarks"),
        ):
            match = self._find_match_for_group(video_stem, key, root_index, entries, label, kind, _notify)
            if match is not None:
                return match

        for label, entries, kind in (
            ("token overlap (chapters)", self._chapter_entries, "chapters"),
            ("token overlap (bookmarks)", self._bookmark_entries, "bookmarks"),
        ):
            match = self._find_token_match(video_stem, entries, label, kind, _notify)
            if match is not None:
                return match

        for label, entries, kind in (
            ("fuzzy logic (chapters)", self._chapter_entries, "chapters"),
            ("fuzzy logic (bookmarks)", self._bookmark_entries, "bookmarks"),
        ):
            match = self._find_fuzzy_match(video_stem, entries, label, kind, _notify)
            if match is not None:
                return match

        return None

    def _find_match_for_group(
        self,
        video_stem: str,
        key: str,
        index: dict[str, list[Path]],
        entries: list[tuple[str, list[str], Path]],
        label: str,
        kind: str,
        notify_fn: Callable[[str, bool], None],
    ) -> tuple[Path, str] | None:
        match = self._pick_best(index.get(key, []))
        if match is not None:
            notify_fn(label, True)
            return match, kind
        notify_fn(label, False)
        return None

    def _find_token_match(
        self,
        video_stem: str,
        entries: list[tuple[str, list[str], Path]],
        label: str,
        kind: str,
        notify_fn: Callable[[str, bool], None],
    ) -> tuple[Path, str] | None:
        match = self._pick_best_token_overlap(video_stem, entries)
        if match is not None:
            notify_fn(label, True)
            return match, kind
        notify_fn(label, False)
        return None

    def _find_fuzzy_match(
        self,
        video_stem: str,
        entries: list[tuple[str, list[str], Path]],
        label: str,
        kind: str,
        notify_fn: Callable[[str, bool], None],
    ) -> tuple[Path, str] | None:
        match = self._pick_best_fuzzy_ratio(video_stem, entries)
        if match is not None:
            notify_fn(label, True)
            return match, kind
        notify_fn(label, False)
        return None

    def _build_index(self, root: Path) -> dict[str, list[Path]]:
        index: dict[str, list[Path]] = {}
        if not root.exists() or not root.is_dir():
            return index
        for path in root.rglob("*.txt"):
            key = _normalize_name(path.stem)
            if not key:
                continue
            index.setdefault(key, []).append(path)
        return index

    def _pick_best(self, candidates: list[Path]) -> Optional[Path]:
        if not candidates:
            return None
        return min(candidates, key=lambda p: len(p.stem))

    def _build_entries(self, root: Path) -> list[tuple[str, list[str], Path]]:
        entries: list[tuple[str, list[str], Path]] = []
        if not root.exists() or not root.is_dir():
            return entries
        for path in root.rglob("*.txt"):
            tokens = _normalize_tokens(path.stem)
            normalized = "".join(tokens)
            if not normalized:
                continue
            entries.append((normalized, tokens, path))
        return entries

    def _pick_best_token_overlap(self, target_raw: str, entries: list[tuple[str, list[str], Path]]) -> Optional[Path]:
        target_tokens = _normalize_tokens(target_raw)
        target_normalized = "".join(target_tokens)
        if not target_normalized:
            return None
        winner: tuple[float, float, int, Path] | None = None
        for normalized, tokens, path in entries:
            overlap = _token_overlap_score(target_tokens, tokens)
            if overlap < MIN_TOKEN_OVERLAP:
                continue
            ratio = _fuzzy_ratio(target_normalized, normalized)
            score = (overlap, ratio, -len(path.stem), path)
            if winner is None or score > winner:
                winner = score
        return winner[3] if winner is not None else None

    def _pick_best_fuzzy_ratio(self, target_raw: str, entries: list[tuple[str, list[str], Path]]) -> Optional[Path]:
        target_tokens = _normalize_tokens(target_raw)
        target_normalized = "".join(target_tokens)
        if not target_normalized:
            return None
        winner: tuple[float, float, int, Path] | None = None
        for normalized, tokens, path in entries:
            ratio = _fuzzy_ratio(target_normalized, normalized)
            if ratio < MIN_FUZZY_RATIO:
                continue
            overlap = _token_overlap_score(target_tokens, tokens)
            score = (overlap, ratio, -len(path.stem), path)
            if winner is None or score > winner:
                winner = score
        return winner[3] if winner is not None else None
