from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .marks.bookmarks_reader import BookmarksFileReader
from .marks.mchapters import (
    DEFAULT_LANGUAGE,
    DEFAULT_TIMESCALE,
    create_mchapters_document,
)


def _sanitize_filename_component(name: str) -> str:
    return name.replace("/", "_")


def _default_output_path(bookmarks_path: Path, title: str) -> Path:
    safe_title = _sanitize_filename_component(title)
    return bookmarks_path.with_name(f"{safe_title}.txt")


def convert_bookmarks_to_mchapters(
    bookmarks_path: Path,
    *,
    output_path: Optional[Path] = None,
    language: str = DEFAULT_LANGUAGE,
    time_scale: int = DEFAULT_TIMESCALE,
    title: Optional[str] = None,
) -> Path:
    reader = BookmarksFileReader()
    chapters = reader.read(str(bookmarks_path))
    document = create_mchapters_document(
        bookmarks_path,
        chapters,
        language=language,
        time_scale=time_scale,
        title=title,
    )

    target_path = output_path or _default_output_path(bookmarks_path, document.title)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(document.to_string(), encoding="utf-8")
    return target_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="bookmarks_to_mchapters")
    parser.add_argument("bookmark", help="Path to the bookmarks file")
    parser.add_argument("--output", help="Output path for the chapters file")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="Chapter language label")
    parser.add_argument(
        "--timescale",
        type=int,
        default=DEFAULT_TIMESCALE,
        help="Time scale for mChapters metadata",
    )
    parser.add_argument("--title", help="Override document title")

    args = parser.parse_args(argv)

    bookmark_path = Path(args.bookmark)
    output_path = Path(args.output) if args.output else None

    result_path = convert_bookmarks_to_mchapters(
        bookmark_path,
        output_path=output_path,
        language=args.language,
        time_scale=args.timescale,
        title=args.title,
    )
    print(f"Wrote {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
