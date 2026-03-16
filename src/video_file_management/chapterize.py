from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable, List, Optional

DEFAULT_CHAPTERS_DIR = (
    Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Personal" / "Zetc" / "Chapters"
)


def find_chapters_file_for(video_path: Path, chapters_dir: Path = DEFAULT_CHAPTERS_DIR) -> Optional[Path]:
    """Try to locate a chapters file for `video_path` in `chapters_dir`.

    Strategy:
    - Exact match: `<stem>.txt`
    - Substring (case-insensitive) first-match fallback
    """
    stem = video_path.stem
    if not chapters_dir.exists() or not chapters_dir.is_dir():
        return None
    exact = chapters_dir / f"{stem}.txt"
    if exact.exists():
        return exact

    # Fallback: simple substring search (case-insensitive)
    lower_stem = stem.lower()
    for p in chapters_dir.iterdir():
        if not p.is_file():
            continue
        if lower_stem in p.name.lower():
            return p
    return None


def convert_to_mp4(src: Path, dest: Path) -> bool:
    """Attempt to convert/remux `src` to MP4 at `dest`.

    Try remuxing (`-c copy`) first to avoid re-encode. If that fails,
    fall back to a conservative re-encode using `libx264`/`aac`.
    Returns True on success.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg not found in PATH; cannot convert files.")
        return False

    # Try remux (fast, no re-encode)
    cmd_copy = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-c",
        "copy",
        "-y",
        str(dest),
    ]
    try:
        subprocess.run(cmd_copy, check=True)
        return True
    except Exception:
        pass

    # Fall back to re-encode
    cmd_reencode = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-y",
        str(dest),
    ]
    try:
        subprocess.run(cmd_reencode, check=True)
        return True
    except Exception:
        return False


def prompt_after_batch() -> str:
    """Interactive prompt after processing a batch.

    Returns one of: 'continue', 'quit', 'finish'
    """
    try:
        while True:
            resp = input("Batch finished — choose [continue|quit|finish]: ").strip().lower()
            if resp in ("continue", "quit", "finish"):
                return resp
    except KeyboardInterrupt:
        return "quit"


def _embed_mp4_candidates(
    candidates: List[Path],
    chapters_dir: Path,
    reader: Any,
    writer: Any,
    test_mode: bool,
) -> int:
    """Embed chapters into MP4/MOV files. Returns number processed."""
    processed = 0
    for p in candidates:
        if test_mode and processed >= 10:
            break
        chapters_path = find_chapters_file_for(p, chapters_dir)
        if not chapters_path:
            print(f"No chapters file found for {p.name}")
            continue
        chapters = reader.read(str(chapters_path))
        print(f"Embedding chapters into {p.name} using {chapters_path.name}")
        writer.write(str(p), chapters)
        processed += 1
    return processed


def _convert_and_embed_batch(
    batch: List[Path],
    chapters_dir: Path,
    reader: Any,
    writer: Any,
    test_mode: bool,
    processed: int,
) -> int:
    """Convert a batch of non-MP4 files and embed chapters. Returns number processed."""
    for src in batch:
        if test_mode and processed >= 10:
            break
        chapters_path = find_chapters_file_for(src, chapters_dir)
        if not chapters_path:
            print(f"No chapters file found for {src.name}; skipping")
            continue
        dest = src.parent / (src.stem + ".converted.mp4")
        ok = convert_to_mp4(src, dest)
        if not ok:
            print(f"Conversion failed for {src}; skipping")
            continue
        chapters = reader.read(str(chapters_path))
        print(f"Embedding chapters into converted file {dest.name}")
        writer.write(str(dest), chapters)
        processed += 1
    return processed


def process_files(
    files: Iterable[Path],
    chapters_dir: Path = DEFAULT_CHAPTERS_DIR,
    queue_size: int = 100,
    test_mode: bool = False,
    interactive: bool = True,
) -> None:
    """Process files with MP4 priority and conversion queue semantics.

    - MP4/MOV files attempted first.
    - Non-MP4 files are converted in batches of `queue_size`.
    """
    from video_file_management.marks.readers import ChaptersFileReader
    from video_file_management.marks.writers import MP4ChaptersWriter

    mp4_writer = MP4ChaptersWriter()
    reader = ChaptersFileReader()

    files = list(files)
    if test_mode:
        files = files[:10]

    mp4_candidates: List[Path] = []
    convert_candidates: List[Path] = []

    for p in files:
        suf = p.suffix.lower().lstrip(".")
        if suf in ("mp4", "mov"):
            mp4_candidates.append(p)
        else:
            convert_candidates.append(p)

    processed = _embed_mp4_candidates(mp4_candidates, chapters_dir, reader, mp4_writer, test_mode)

    # Process conversion queue in batches
    for idx in range(0, len(convert_candidates), queue_size):
        batch = convert_candidates[idx : idx + queue_size]
        processed = _convert_and_embed_batch(batch, chapters_dir, reader, mp4_writer, test_mode, processed)

        if test_mode and processed >= 10:
            break

        if interactive:
            choice = prompt_after_batch()
            if choice == "quit":
                print("Quitting after current batch")
                break
            if choice == "finish":
                interactive = False


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="chapterize")
    parser.add_argument("paths", nargs="+", help="Files or directories to process")
    parser.add_argument("--queue-size", type=int, default=100, help="Batch size for conversion queue")
    parser.add_argument("--test-mode", action="store_true", help="Limit processing to 10 files for testing")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt between batches (finish automatically)",
    )
    parser.add_argument("--chapters-dir", default=str(DEFAULT_CHAPTERS_DIR), help="Chapters directory to search")

    args = parser.parse_args(argv)

    # Resolve input paths
    all_files: List[Path] = []
    for p in args.paths:
        path = Path(p)
        if path.is_dir():
            for f in path.rglob("*"):
                if f.is_file():
                    all_files.append(f)
        elif path.exists():
            all_files.append(path)

    chapters_dir = Path(args.chapters_dir)
    process_files(
        all_files,
        chapters_dir=chapters_dir,
        queue_size=args.queue_size,
        test_mode=args.test_mode,
        interactive=not args.non_interactive,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
