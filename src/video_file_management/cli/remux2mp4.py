from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from video_file_management.remux.remux2mp4 import (
    VERSION,
    CommandRunner,
    Remux2Mp4Config,
    Remux2Mp4Service,
    RemuxStatus,
)

REENCODE_VIDEO_CODEC = "libx264"
REENCODE_PRESET = "medium"
REENCODE_CRF = 18
REENCODE_AUDIO_CODEC = "aac"
REENCODE_AUDIO_BITRATE = "192k"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="remux2mp4",
        description="Losslessly re-container supported files into MP4 using ffmpeg.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Input file or directory. Defaults to current directory.",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="Output file or directory. Defaults to same directory.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan directories recursively.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without converting.",
    )
    parser.add_argument("--verbose", action="store_true", help="Show ffmpeg output.")
    parser.add_argument("--log", type=Path, help="Write ffmpeg output to a log file.")
    parser.add_argument("--version", action="store_true", help="Show version and exit.")
    parser.add_argument(
        "--reencode-incompatible",
        action="store_true",
        help="Reencode incompatible files after remuxing without prompting.",
    )
    parser.add_argument(
        "--no-reencode",
        action="store_true",
        help="Skip the reencode prompt for incompatible files.",
    )
    return parser


def build_service() -> Remux2Mp4Service:
    return Remux2Mp4Service()


def _render_result(result) -> str:
    name = result.input_path.name
    if result.status == RemuxStatus.CONVERTED:
        return f"OK: {name} -> {result.output_path.name}"
    if result.status == RemuxStatus.DRY_RUN:
        return f"DRY RUN: {name} -> {result.output_path.name}"
    if result.status == RemuxStatus.SKIPPED:
        return f"SKIP: {name} ({result.message})"
    if result.status == RemuxStatus.INCOMPATIBLE:
        return f"INCOMPATIBLE: {name} ({result.message})"
    return f"FAIL: {name} ({result.message})"


def _prompt_reencode(incompatible) -> bool:
    print("\nIncompatible files:")
    for result in incompatible:
        detail = ", ".join(result.warnings) if result.warnings else result.message
        print(f"- {result.input_path.name}: {detail}")
    resp = input("Reencode these files to MP4? [y/N]: ").strip().lower()
    return resp in {"y", "yes"}


def _build_reencode_command(input_path: Path, output_path: Path, *, verbose: bool) -> list[str]:
    log_level = "info" if verbose else "error"
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        log_level,
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v",
        "-map",
        "0:a?",
        "-map",
        "0:s?",
        "-c:v",
        REENCODE_VIDEO_CODEC,
        "-preset",
        REENCODE_PRESET,
        "-crf",
        str(REENCODE_CRF),
        "-c:a",
        REENCODE_AUDIO_CODEC,
        "-b:a",
        REENCODE_AUDIO_BITRATE,
        "-c:s",
        "mov_text",
        "-map_metadata",
        "0",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def _reencode_incompatible(incompatible, *, dry_run: bool, verbose: bool, log_file: Optional[Path]) -> bool:
    runner = CommandRunner()
    had_failure = False
    for result in incompatible:
        if dry_run:
            print(f"DRY RUN: reencode {result.input_path.name} -> {result.output_path.name}")
            continue
        cmd = _build_reencode_command(result.input_path, result.output_path, verbose=verbose)
        run_result = runner.run(cmd, capture_output=not verbose)
        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8") as handle:
                if run_result.stdout:
                    handle.write(run_result.stdout)
                if run_result.stderr:
                    handle.write(run_result.stderr)
        if run_result.returncode == 0:
            print(f"ENCODED: {result.input_path.name} -> {result.output_path.name}")
        else:
            had_failure = True
            print(f"FAIL: {result.input_path.name} (reencode failed)")
    return had_failure


def _handle_incompatible(incompatible, args) -> tuple[bool, bool]:
    """Handle incompatible files. Returns (did_reencode, reencode_failed)."""
    if args.no_reencode:
        print("Incompatible files skipped; use --reencode-incompatible to reencode.")
        return False, False

    should_reencode = args.reencode_incompatible
    if not should_reencode and sys.stdin.isatty():
        should_reencode = _prompt_reencode(incompatible)
    if should_reencode:
        failed = _reencode_incompatible(
            incompatible,
            dry_run=args.dry_run,
            verbose=args.verbose,
            log_file=args.log,
        )
        return True, failed

    print("Incompatible files not reencoded.")
    return False, False


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.version:
        print(f"remux2mp4 version {VERSION}")
        return 0

    config = Remux2Mp4Config(
        input_path=args.input,
        output_path=args.output,
        recursive=args.recursive,
        dry_run=args.dry_run,
        verbose=args.verbose,
        log_file=args.log,
    )

    service = build_service()
    try:
        results = service.run(config)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    if results:
        print(f"Found {len(results)} file(s). Starting conversion...")

    for result in results:
        for warning in result.warnings:
            print(f"WARN: {result.input_path.name}: {warning}")
        print(_render_result(result))

    incompatible = [r for r in results if r.status == RemuxStatus.INCOMPATIBLE]
    did_reencode, reencode_failed = False, False
    if incompatible:
        did_reencode, reencode_failed = _handle_incompatible(incompatible, args)

    failed = [r for r in results if r.status == RemuxStatus.FAILED]
    if failed or reencode_failed:
        return 1
    if incompatible and not did_reencode:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
