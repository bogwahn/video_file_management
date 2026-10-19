"""Find videos that correspond to chapters/bookmarks files."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Protocol, Sequence

from .config import MIN_FUZZY_RATIO, MIN_TOKEN_OVERLAP, VIDEO_EXTENSIONS
from .path_match_index import _fuzzy_ratio, _normalize_name, _normalize_tokens, _token_overlap_score


class VideoLocatorLike(Protocol):
    def find_video_for_marks_file(
        self, marks_file: Path, *, notify_fn: Optional[Callable[[str], None]] = None
    ) -> Optional[Path]: ...


class VideoLocator:
    """Find videos that correspond to chapters/bookmarks files."""

    def __init__(self, roots: Sequence[Path]) -> None:
        self._roots = roots

    def find_video_for_marks_file(
        self, marks_file: Path, *, notify_fn: Optional[Callable[[str], None]] = None
    ) -> Optional[Path]:
        def _notify(label: str, found: bool) -> None:
            if notify_fn:
                status = "Found!" if found else "Not Found"
                notify_fn(f"  method: {label:<26}  {status}")

        target = _normalize_name(marks_file.stem)
        target_tokens = _normalize_tokens(marks_file.stem)
        candidates = self._collect_video_candidates()

        exact = self._find_exact_match(target, candidates)
        if exact is not None:
            _notify("exact match", True)
            return exact
        _notify("exact match", False)

        token_best = self._find_best_token_overlap(target, target_tokens, candidates)
        if token_best is not None:
            _notify("token overlap", True)
            return token_best
        _notify("token overlap", False)

        fuzzy_best = self._find_best_fuzzy_match(target, target_tokens, candidates)
        if fuzzy_best is not None:
            _notify("fuzzy logic", True)
            return fuzzy_best
        _notify("fuzzy logic", False)
        return None

    def _collect_video_candidates(self) -> list[tuple[str, list[str], Path]]:
        candidates: list[tuple[str, list[str], Path]] = []
        for root in self._roots:
            if not root.exists() or not root.is_dir():
                continue
            for candidate in root.rglob("*"):
                if not candidate.is_file() or candidate.suffix.lower() not in VIDEO_EXTENSIONS:
                    continue
                candidates.append((_normalize_name(candidate.stem), _normalize_tokens(candidate.stem), candidate))
        return candidates

    def _find_exact_match(self, target: str, candidates: list[tuple[str, list[str], Path]]) -> Optional[Path]:
        for c_norm, _, path in candidates:
            if c_norm == target:
                return path
        return None

    def _find_best_token_overlap(
        self,
        target: str,
        target_tokens: list[str],
        candidates: list[tuple[str, list[str], Path]],
    ) -> Optional[Path]:
        best: tuple[float, float, int, Path] | None = None
        for c_norm, c_toks, path in candidates:
            overlap = _token_overlap_score(target_tokens, c_toks)
            if overlap < MIN_TOKEN_OVERLAP:
                continue
            ratio = _fuzzy_ratio(target, c_norm)
            score = (overlap, ratio, -len(path.stem), path)
            if best is None or score > best:
                best = score
        return best[3] if best is not None else None

    def _find_best_fuzzy_match(
        self,
        target: str,
        target_tokens: list[str],
        candidates: list[tuple[str, list[str], Path]],
    ) -> Optional[Path]:
        best: tuple[float, float, int, Path] | None = None
        for c_norm, c_toks, path in candidates:
            ratio = _fuzzy_ratio(target, c_norm)
            if ratio < MIN_FUZZY_RATIO:
                continue
            overlap = _token_overlap_score(target_tokens, c_toks)
            score = (overlap, ratio, -len(path.stem), path)
            if best is None or score > best:
                best = score
        return best[3] if best is not None else None
