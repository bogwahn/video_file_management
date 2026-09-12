"""Post-download resolution enrichment via in-repo ffprobe helpers.

When a download filename omits resolution (unknown at title/download time),
FileWatcher probes the file with ``video_file_management.metadata_reader``
(ffprobe) and, if dimensions map to a known token, renames to insert
``.{resolution}.`` before the VR/ext suffix.

Does not invent a new probe stack — reuses ``read_file_metadata``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from video_file_management.metadata_reader import read_file_metadata
from video_file_management.zephyr.parser import (
    ParsedFilename,
    build_filename,
    resolution_from_dimensions,
)

log = logging.getLogger(__name__)


def probe_resolution_token(path: Path) -> str | None:
    """Return a Zephyr resolution token from ffprobe dimensions, or None."""
    meta = read_file_metadata(path)
    if meta.errors:
        log.debug("ffprobe enrichment errors for %s: %s", path.name, meta.errors)
    return resolution_from_dimensions(meta.video.width, meta.video.height)


def enrich_parsed_with_probe(path: Path, parsed: ParsedFilename) -> ParsedFilename | None:
    """If ``parsed.resolution`` is missing, probe and return an updated ParsedFilename.

    Returns None when enrichment is not needed or probe cannot resolve a token.
    Does not rename on disk — caller applies the rename.
    """
    if parsed.resolution:
        return None
    token = probe_resolution_token(path)
    if not token:
        log.info("No resolution probe result for %s; leaving name without resolution", path.name)
        return None
    new_name = build_filename(
        actors=list(parsed.actors),
        studio=parsed.studio,
        title=parsed.title,
        resolution=token,
        extension=parsed.extension,
        is_vr=parsed.is_vr,
    )
    return ParsedFilename(
        actors=parsed.actors,
        studio=parsed.studio,
        title=parsed.title,
        resolution=token,
        is_vr=parsed.is_vr,
        extension=parsed.extension,
        filename=new_name,
        warnings=parsed.warnings + (f"enriched resolution={token} via ffprobe",),
    )


def apply_resolution_enrichment(
    real_path: Path,
    parsed: ParsedFilename,
    *,
    symlink_paths: tuple[Path, ...] = (),
) -> tuple[Path, ParsedFilename, tuple[Path, ...]]:
    """Probe + rename when resolution was omitted; refresh secondary VR symlinks.

    Returns ``(path, parsed, symlink_paths)`` — unchanged when no enrichment applies.
    """
    updated = enrich_parsed_with_probe(real_path, parsed)
    if updated is None or updated.filename == real_path.name:
        return real_path, parsed, symlink_paths

    dest = real_path.with_name(updated.filename)
    if dest.exists() or dest.is_symlink():
        log.warning(
            "Enrichment rename blocked (dest exists): %s -> %s",
            real_path.name,
            dest.name,
        )
        return real_path, parsed, symlink_paths

    log.info("Enriching resolution: %s -> %s", real_path.name, dest.name)
    real_path.rename(dest)

    new_links: list[Path] = []
    for link in symlink_paths:
        new_link = link.with_name(updated.filename)
        try:
            if link.is_symlink() or link.exists():
                link.unlink()
            new_link.parent.mkdir(parents=True, exist_ok=True)
            if not new_link.exists() and not new_link.is_symlink():
                new_link.symlink_to(dest)
            new_links.append(new_link)
        except OSError as exc:
            log.warning("Failed to refresh secondary link %s: %s", link, exc)
            if link.exists() or link.is_symlink():
                new_links.append(link)

    # Ensure link targets still resolve if we only renamed the real file.
    for link in new_links:
        try:
            if link.is_symlink() and Path(os.path.realpath(link)) != Path(os.path.realpath(dest)):
                link.unlink()
                link.symlink_to(dest)
        except OSError:
            pass

    return dest, updated, tuple(new_links)
