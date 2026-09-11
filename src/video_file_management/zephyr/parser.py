"""Filename grammar parser/builder for Zephyr download core.

Grammar (locked):
  {Actors}.{Studio}.{Title}.{Resolution}[.VR].{ext}

Actors: First.Last, joined with .And., max 3.
Resolution: dotted token (480p|540p|720p|1080p|2k|4k).
VR marker: literal .VR immediately before extension when is_vr.
No whitespace; Title.Case words separated by dots.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RESOLUTIONS = frozenset({"480p", "540p", "720p", "1080p", "2k", "4k"})
VIDEO_EXTENSIONS = frozenset({"mp4", "mkv", "mov", "webm", "m4v", "avi", "wmv", "ts"})
ILLEGAL_CHARS = re.compile(r'[/\\:*"<>|]')
MAX_FILENAME_LEN = 150
MAX_ACTORS = 3

# Actor token: Title.Case word (letters/digits; leading capital preferred but not required for parse)
_WORD = re.compile(r"^[A-Za-z0-9]+$")


class ParseError(ValueError):
    """Filename does not conform to the locked Zephyr grammar."""


@dataclass(frozen=True)
class ParsedFilename:
    actors: tuple[str, ...]
    studio: str
    title: str
    resolution: str
    is_vr: bool
    extension: str
    filename: str
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def first_actress(self) -> str:
        return self.actors[0] if self.actors else ""


def _title_case_word(word: str) -> str:
    if not word:
        return word
    return word[0].upper() + word[1:].lower()


def _normalize_token_words(raw: str, *, join: str = ".") -> str:
    cleaned = ILLEGAL_CHARS.sub("", raw.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    words = [w for w in cleaned.replace(".", " ").split(" ") if w]
    return join.join(_title_case_word(w) for w in words)


def normalize_actor(raw: str) -> str:
    """Normalize to First.Last (dot-separated, no whitespace)."""
    return _normalize_token_words(raw, join=".")


def normalize_studio(raw: str) -> str:
    """Normalize studio to Capitalized.dotted words (no whitespace)."""
    return _normalize_token_words(raw, join=".")


def normalize_title(raw: str) -> str:
    return _normalize_token_words(raw, join=".")


def normalize_resolution(raw: str | None) -> str | None:
    if not raw:
        return None
    t = raw.lower().strip().lstrip(".")
    for res in ("1080p", "720p", "540p", "480p", "4k", "2k"):
        if res in t:
            return res
    return None


def build_filename(
    *,
    actors: list[str] | tuple[str, ...],
    studio: str,
    title: str,
    resolution: str,
    extension: str = "mp4",
    is_vr: bool = False,
    max_length: int = MAX_FILENAME_LEN,
) -> str:
    """Build a conforming filename; truncates title first if over max_length."""
    norm_actors = [normalize_actor(a) for a in actors if a and str(a).strip()]
    if len(norm_actors) > MAX_ACTORS:
        norm_actors = norm_actors[:MAX_ACTORS]
    if not norm_actors:
        raise ParseError("at least one actor is required")
    studio_n = normalize_studio(studio)
    title_n = normalize_title(title)
    res = normalize_resolution(resolution)
    if not studio_n:
        raise ParseError("studio is required")
    if not title_n:
        raise ParseError("title is required")
    if not res or res not in RESOLUTIONS:
        raise ParseError(f"resolution must be one of {sorted(RESOLUTIONS)}")
    ext = extension.lower().lstrip(".")
    if not ext:
        raise ParseError("extension is required")

    actor_block = ".And.".join(norm_actors)
    vr_part = ".VR" if is_vr else ""
    # Assemble; shrink title if needed
    while True:
        name = f"{actor_block}.{studio_n}.{title_n}.{res}{vr_part}.{ext}"
        if len(name) <= max_length:
            return name
        parts = title_n.split(".")
        if len(parts) <= 1:
            # last resort: hard truncate title token
            overhead = len(name) - len(title_n)
            keep = max(1, max_length - overhead)
            title_n = title_n[:keep].rstrip(".")
            if not title_n:
                raise ParseError("cannot fit filename under max length")
            continue
        title_n = ".".join(parts[:-1])


def _looks_like_name_token(token: str) -> bool:
    return bool(_WORD.match(token)) and token[0].isalpha()


def _parse_actors_from_left(tokens: list[str]) -> tuple[tuple[str, ...], list[str], list[str]]:
    """Consume actors as First.Last (.And. First.Last)* from the left.

    Returns (actors, remaining_tokens, warnings).
    """
    warnings: list[str] = []
    if len(tokens) < 2:
        raise ParseError("expected at least First.Last actor tokens")

    actors: list[str] = []
    i = 0
    while i + 1 < len(tokens):
        first, last = tokens[i], tokens[i + 1]
        if not (_looks_like_name_token(first) and _looks_like_name_token(last)):
            break
        if first.lower() == "and" or last.lower() == "and":
            break
        actors.append(f"{first}.{last}")
        i += 2
        if i >= len(tokens):
            break
        if tokens[i].lower() == "and":
            i += 1
            continue
        break

    if not actors:
        raise ParseError("could not parse First.Last actor from filename")

    if len(actors) > MAX_ACTORS:
        warnings.append(f"truncated actors from {len(actors)} to {MAX_ACTORS}")
        actors = actors[:MAX_ACTORS]
        # remaining tokens after truncation are ambiguous; leave as-is from i

    return tuple(actors), tokens[i:], warnings


def parse_filename(name: str | Path) -> ParsedFilename:
    """Parse a Zephyr-grammar basename. Raises ParseError if non-conforming."""
    filename = Path(name).name
    if not filename or " " in filename:
        raise ParseError("filename must be non-empty and contain no whitespace")
    if ILLEGAL_CHARS.search(filename):
        raise ParseError("filename contains illegal filesystem characters")

    parts = filename.split(".")
    if len(parts) < 5:
        # minimum: First.Last.Studio.Title.Res.ext  → 6 tokens; or First.Last.S.T.4k.mp4
        # First.Last + studio(1) + title(1) + res + ext = 6
        raise ParseError("filename has too few dotted segments")

    ext = parts[-1].lower()
    if ext not in VIDEO_EXTENSIONS:
        raise ParseError(f"unsupported or missing video extension: .{ext}")

    body = parts[:-1]
    is_vr = False
    if body and body[-1].upper() == "VR":
        is_vr = True
        body = body[:-1]

    if not body:
        raise ParseError("missing resolution token")
    resolution = body[-1].lower()
    if resolution not in RESOLUTIONS:
        raise ParseError(f"missing or invalid resolution token before extension: {resolution!r}")
    body = body[:-1]

    actors, rest, warnings = _parse_actors_from_left(body)
    if len(rest) < 2:
        raise ParseError("expected studio and title tokens after actors")

    # Heuristic: first remaining token(s) until we have ≥1 title token.
    # Prefer single-token studio when rest has ≥2 tokens; if multi-word studio
    # was dotted (Blacked.Raw), we cannot perfectly split — spike default:
    # studio = first token, title = remaining tokens joined.
    studio = rest[0]
    title_tokens = rest[1:]
    if not title_tokens:
        raise ParseError("title is required")
    title = ".".join(title_tokens)

    return ParsedFilename(
        actors=actors,
        studio=studio,
        title=title,
        resolution=resolution,
        is_vr=is_vr,
        extension=ext,
        filename=filename,
        warnings=tuple(warnings),
    )


def try_parse_filename(name: str | Path) -> ParsedFilename | None:
    try:
        return parse_filename(name)
    except ParseError:
        return None
