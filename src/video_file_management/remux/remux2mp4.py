from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

import send2trash

VERSION = "1.1.0"
SUPPORTED_INPUT_EXTENSIONS = frozenset({".mkv", ".mpg", ".mpeg", ".f4v"})
FFPROBE_TIMEOUT_SECONDS = 30
FFMPEG_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class Remux2Mp4Config:
    input_path: Optional[Path] = None
    output_path: Optional[Path] = None
    recursive: bool = False
    dry_run: bool = False
    verbose: bool = False
    log_file: Optional[Path] = None
    max_workers: Optional[int] = None


@dataclass(frozen=True)
class RunResult:
    stdout: str
    stderr: str
    returncode: int


@dataclass
class CommandRunner:
    def run(
        self,
        args: Sequence[str],
        *,
        capture_output: bool = True,
        timeout: Optional[int] = None,
    ) -> RunResult:
        try:
            result = subprocess.run(
                list(args),
                capture_output=capture_output,
                text=True,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if stderr:
                stderr = f"{stderr}\n"
            timeout_label = timeout if timeout is not None else "unknown"
            stderr = f"{stderr}command timed out after {timeout_label}s"
            return RunResult(stdout=stdout, stderr=stderr, returncode=124)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        return RunResult(stdout=stdout, stderr=stderr, returncode=result.returncode)


@dataclass(frozen=True)
class StreamInfo:
    index: int
    codec_type: str
    codec_name: str


@dataclass(frozen=True)
class CompatibilityReport:
    incompatible: Tuple[StreamInfo, ...]

    def warning_messages(self) -> Tuple[str, ...]:
        if not self.incompatible:
            return ()
        entries = sorted({f"{s.codec_type}:{s.codec_name}" for s in self.incompatible})
        return (f"incompatible codec(s): {', '.join(entries)}",)


@dataclass
class InputCollector:
    def collect(self, input_path: Optional[Path], recursive: bool) -> list[Path]:
        base = input_path or Path.cwd()

        if base.is_file():
            if base.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
                raise ValueError(f"Input file is not a supported remux source: {base}")
            return [base]

        if recursive:
            paths = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS]
        else:
            paths = [p for p in base.glob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS]

        return sorted(paths, key=lambda p: str(p))


@dataclass
class OutputPlanner:
    def build_output_path(self, input_file: Path, output_arg: Optional[Path]) -> Path:
        if output_arg is None:
            return input_file.with_suffix(".mp4")

        if output_arg.is_dir():
            return output_arg / f"{input_file.stem}.mp4"

        return output_arg


@dataclass
class StreamProbe:
    runner: CommandRunner = field(default_factory=CommandRunner)

    def probe(self, path: Path) -> Tuple[StreamInfo, ...]:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=index,codec_type,codec_name",
            "-of",
            "json",
            str(path),
        ]
        result = self.runner.run(cmd, capture_output=True, timeout=FFPROBE_TIMEOUT_SECONDS)
        if result.returncode != 0 or not result.stdout:
            return ()
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return ()

        streams = []
        for stream in payload.get("streams", []):
            codec_type = stream.get("codec_type")
            codec_name = stream.get("codec_name")
            if not codec_type or not codec_name:
                continue
            streams.append(
                StreamInfo(
                    index=int(stream.get("index", 0)),
                    codec_type=str(codec_type),
                    codec_name=str(codec_name),
                )
            )
        return tuple(streams)


@dataclass(frozen=True)
class Mp4CompatibilityPolicy:
    video_codecs: frozenset[str] = frozenset({"h264", "hevc", "mpeg4"})
    audio_codecs: frozenset[str] = frozenset({"aac", "mp3", "ac3"})
    mpg_video_codecs: frozenset[str] = frozenset({"h264"})
    mpg_audio_codecs: frozenset[str] = frozenset({"aac"})

    def check(self, input_path: Path, streams: Iterable[StreamInfo]) -> CompatibilityReport:
        video_codecs, audio_codecs = self._allowed_codecs(input_path)
        incompatible = []
        for stream in streams:
            if stream.codec_type == "video" and stream.codec_name not in video_codecs:
                incompatible.append(stream)
            elif stream.codec_type == "audio" and stream.codec_name not in audio_codecs:
                incompatible.append(stream)
        return CompatibilityReport(incompatible=tuple(incompatible))

    def _allowed_codecs(self, input_path: Path) -> tuple[frozenset[str], frozenset[str]]:
        ext = input_path.suffix.lower().lstrip(".")
        if ext in {"mpg", "mpeg"}:
            return self.mpg_video_codecs, self.mpg_audio_codecs
        return self.video_codecs, self.audio_codecs


@dataclass(frozen=True)
class RemuxJob:
    input_path: Path
    output_path: Path
    compatible: bool
    warnings: Tuple[str, ...] = ()


class RemuxStatus:
    CONVERTED = "converted"
    SKIPPED = "skipped"
    FAILED = "failed"
    DRY_RUN = "dry-run"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class RemuxResult:
    input_path: Path
    output_path: Path
    status: str
    message: str
    warnings: Tuple[str, ...] = ()


@dataclass
class RemuxPlanner:
    probe: StreamProbe = field(default_factory=StreamProbe)
    policy: Mp4CompatibilityPolicy = field(default_factory=Mp4CompatibilityPolicy)

    def plan(self, input_file: Path, output_path: Path) -> RemuxJob:
        streams = self.probe.probe(input_file)
        report = self.policy.check(input_file, streams)
        compatible = not report.incompatible
        return RemuxJob(
            input_path=input_file,
            output_path=output_path,
            compatible=compatible,
            warnings=report.warning_messages(),
        )


@dataclass
class FfmpegCommandBuilder:
    def build(self, job: RemuxJob, *, verbose: bool) -> list[str]:
        log_level = "info" if verbose else "error"
        return [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            log_level,
            "-y",
            "-i",
            str(job.input_path),
            "-map",
            "0:v",
            "-map",
            "0:a?",
            "-map",
            "0:s?",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-map_metadata",
            "0",
            str(job.output_path),
        ]


@dataclass
class RemuxExecutor:
    runner: CommandRunner = field(default_factory=CommandRunner)
    command_builder: FfmpegCommandBuilder = field(default_factory=FfmpegCommandBuilder)

    def remux(
        self,
        job: RemuxJob,
        *,
        dry_run: bool,
        verbose: bool,
        log_file: Optional[Path],
    ) -> RemuxResult:
        if dry_run:
            return RemuxResult(
                input_path=job.input_path,
                output_path=job.output_path,
                status=RemuxStatus.DRY_RUN,
                message="dry run",
                warnings=job.warnings,
            )

        cmd = self.command_builder.build(job, verbose=verbose)
        result = self.runner.run(cmd, capture_output=not verbose, timeout=FFMPEG_TIMEOUT_SECONDS)
        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8") as handle:
                if result.stdout:
                    handle.write(result.stdout)
                if result.stderr:
                    handle.write(result.stderr)

        if result.returncode == 0:
            if job.output_path.exists() and job.output_path.stat().st_size > 1024:
                try:
                    send2trash.send2trash(job.input_path)
                    msg = "converted and trashed original"
                except Exception as e:
                    msg = f"converted but failed to trash original: {e}"

                return RemuxResult(
                    input_path=job.input_path,
                    output_path=job.output_path,
                    status=RemuxStatus.CONVERTED,
                    message=msg,
                    warnings=job.warnings,
                )
            else:
                if job.output_path.exists():
                    job.output_path.unlink()
                return RemuxResult(
                    input_path=job.input_path,
                    output_path=job.output_path,
                    status=RemuxStatus.FAILED,
                    message="ffmpeg produced empty/invalid file",
                    warnings=job.warnings,
                )

        return RemuxResult(
            input_path=job.input_path,
            output_path=job.output_path,
            status=RemuxStatus.FAILED,
            message="ffmpeg timed out" if result.returncode == 124 else "ffmpeg failed",
            warnings=job.warnings,
        )


@dataclass
class Remux2Mp4Service:
    collector: InputCollector = field(default_factory=InputCollector)
    output_planner: OutputPlanner = field(default_factory=OutputPlanner)
    planner: RemuxPlanner = field(default_factory=RemuxPlanner)
    executor: RemuxExecutor = field(default_factory=RemuxExecutor)

    def run(self, config: Remux2Mp4Config) -> list[RemuxResult]:
        input_files = self.collector.collect(config.input_path, config.recursive)
        if not input_files:
            raise ValueError("No remuxable files found.")

        if config.output_path is not None and config.output_path.is_dir():
            config.output_path.mkdir(parents=True, exist_ok=True)

        results: list[RemuxResult] = []
        jobs: list[RemuxJob] = []

        for source in input_files:
            output_path = self.output_planner.build_output_path(source, config.output_path)
            if output_path.exists() and output_path.stat().st_mtime >= source.stat().st_mtime:
                results.append(
                    RemuxResult(
                        input_path=source,
                        output_path=output_path,
                        status=RemuxStatus.SKIPPED,
                        message="already converted",
                    )
                )
                continue

            job = self.planner.plan(source, output_path)
            if not job.compatible:
                results.append(
                    RemuxResult(
                        input_path=source,
                        output_path=output_path,
                        status=RemuxStatus.INCOMPATIBLE,
                        message="incompatible codecs",
                        warnings=job.warnings,
                    )
                )
                continue
            jobs.append(job)

        if not jobs:
            return results

        max_workers = config.max_workers or (os.cpu_count() or 1)
        if max_workers > 1 and len(jobs) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_map = {
                    pool.submit(
                        self.executor.remux,
                        job,
                        dry_run=config.dry_run,
                        verbose=config.verbose,
                        log_file=config.log_file,
                    ): job
                    for job in jobs
                }
                for future in as_completed(future_map):
                    results.append(future.result())
        else:
            for job in jobs:
                results.append(
                    self.executor.remux(
                        job,
                        dry_run=config.dry_run,
                        verbose=config.verbose,
                        log_file=config.log_file,
                    )
                )

        return results
