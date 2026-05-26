# Architecture: video-file-management

Written as a clean-slate design. No legacy constraints.

---

## Vision

A suite of stackable, single-word CLI commands for creating and managing a video file library. The library spans multiple storage protocols (SMB, AFP, local) and will eventually serve files over multiple streaming protocols (HLS, DASH). Each command is a thin CLI wrapper over a composable domain layer.

---

## Principles

1. **Protocol-first.** Every extension point is a Protocol. Concrete implementations are injected.
2. **Commands own nothing.** Business logic lives in the domain. Commands are thin orchestrators.
3. **Readers read, writers write.** No class reads and writes. No reader knows about writers.
4. **Errors are values.** No silent swallowing. No bare raises. Results carry errors as data.
5. **Single responsibility.** Every class does one thing. Every module owns one concept.
6. **Storage is an abstraction.** Commands never touch the filesystem directly.

---

## Folder Structure

```
src/video_file_management/
│
├── commands/                     # CLI entry points + orchestration only
│   ├── chapterize/
│   │   ├── __init__.py
│   │   ├── cli.py                # argparse → ChapterizeOrchestrator
│   │   ├── config.py             # ChapterizeConfig (dataclass)
│   │   ├── orchestrator.py       # ChapterizeOrchestrator
│   │   ├── discovery.py          # VideoDiscovery (match videos to marks files)
│   │   ├── merger.py             # ChapterMerger (merge existing + new marks)
│   │   └── resolver.py           # ConflictResolver (keep / replace / merge)
│   │
│   ├── remux/
│   │   ├── __init__.py
│   │   ├── cli.py                # argparse → RemuxOrchestrator
│   │   ├── config.py             # RemuxConfig (format-agnostic)
│   │   ├── orchestrator.py       # RemuxOrchestrator (injects a FormatService)
│   │   ├── mp4/
│   │   │   ├── __init__.py
│   │   │   ├── config.py         # MP4Config
│   │   │   ├── policy.py         # MP4CompatibilityPolicy
│   │   │   └── service.py        # MP4Service (implements FormatService)
│   │   └── quickaction.py        # macOS Finder Quick Action wrapper
│   │
│   ├── encode/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── config.py             # EncodeConfig
│   │   ├── orchestrator.py       # EncodeOrchestrator (injects a CodecProfile)
│   │   └── profiles/             # h264.py, hevc.py, av1.py, aac.py, etc.
│   │
│   ├── tag/
│   │   ├── __init__.py
│   │   ├── cli.py                # argparse → get / add / remove subcommands
│   │   └── orchestrator.py       # TagOrchestrator (injects TagBackend)
│   │
│   ├── info/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   └── orchestrator.py       # InfoOrchestrator → VideofileMetadataReader
│   │
│   └── name/
│       ├── __init__.py
│       ├── cli.py                # argparse → check / fix / format subcommands
│       ├── checker.py            # NameChecker
│       ├── fixer.py              # NameFixer
│       └── rules.py              # NamingRules (configurable rule engine)
│
├── domain/                       # Pure domain — no CLI, no subprocess calls
│   │
│   ├── videomarks/
│   │   ├── __init__.py
│   │   ├── videomark.py          # VideoMark (Protocol)
│   │   ├── chapter.py            # Chapter (implements VideoMark)
│   │   ├── bookmark.py           # Bookmark (implements VideoMark)
│   │   ├── videomarks_file.py    # VideoMarksFile (Protocol)
│   │   ├── chapters_file.py      # ChaptersFile (implements VideoMarksFile)
│   │   └── bookmarks_file.py     # BookmarksFile (implements VideoMarksFile)
│   │
│   ├── video/
│   │   ├── __init__.py
│   │   ├── video_file.py         # VideoFile (core domain object)
│   │   ├── stream_info.py        # VideoStreamInfo, AudioStreamInfo
│   │   └── compatibility.py      # StreamCompatibility, CompatibilityReport
│   │
│   ├── readers/
│   │   ├── __init__.py
│   │   ├── chapters_file_reader.py      # ChaptersFileReader
│   │   ├── bookmarks_file_reader.py     # BookmarksFileReader
│   │   ├── videofile_reader.py          # VideofileReader (embedded tracks via ffprobe)
│   │   └── videofile_metadata_reader.py # VideofileMetadataReader (streams + format)
│   │
│   ├── writers/
│   │   ├── __init__.py
│   │   ├── chapter_write_strategy.py    # ChapterWriteStrategy (Protocol)
│   │   ├── mp4_chapters_writer.py       # MP4ChaptersWriter (via MP4Box)
│   │   └── xattr_chapters_writer.py     # XattrChaptersWriter (via xattr)
│   │
│   ├── tagging/
│   │   ├── __init__.py
│   │   ├── tag_backend.py        # TagBackend (Protocol), TagResult
│   │   └── finder.py             # FinderTagBackend (xattr / macOS CLI)
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── storage_backend.py    # StorageBackend (Protocol)
│   │   ├── local.py              # LocalBackend
│   │   ├── smb.py                # SMBBackend
│   │   └── afp.py                # AFPBackend
│   │
│   └── shared/
│       ├── __init__.py
│       ├── timecode.py           # parse_timecode, format_timecode
│       ├── command_runner.py     # CommandRunner, CommandResult
│       ├── file_collector.py     # FileCollector (path collection + filtering)
│       └── result.py             # Result[T] (data + errors, no exceptions)
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/
│
├── scripts/
├── deploy/
└── docs/
```

---

## Domain Object Models

### VideoMarks

```python
# domain/videomarks/videomark.py
class VideoMark(Protocol):
    title: str
    timecode: timedelta

# domain/videomarks/chapter.py
@dataclass(frozen=True, slots=True)
class Chapter:
    title: str
    timecode: timedelta

# domain/videomarks/bookmark.py
@dataclass(frozen=True, slots=True)
class Bookmark:
    title: str
    timecode: timedelta

# domain/videomarks/videomarks_file.py
class VideoMarksFile(Protocol):
    file_path: Path

    def add(self, timecode: str, title: str) -> None: ...
    def remove(self, identifier: str | int) -> None: ...
    def marks(self) -> Iterable[VideoMark]: ...
    def to_string(self) -> str: ...

# domain/videomarks/chapters_file.py
@dataclass
class ChaptersFile:
    """VideoMarksFile backed by a list of Chapter objects."""
    file_path: Path
    _marks: list[Chapter] = field(default_factory=list)

    def add(self, timecode: str, title: str) -> None: ...
    def remove(self, identifier: str | int) -> None: ...
    def marks(self) -> Iterable[Chapter]: ...
    def to_string(self) -> str:
        """Serialize as '[HH:MM:SS.mmm] Title' lines."""

# domain/videomarks/bookmarks_file.py
@dataclass
class BookmarksFile:
    """VideoMarksFile backed by a list of Bookmark objects."""
    file_path: Path
    _marks: list[Bookmark] = field(default_factory=list)

    def add(self, timecode: str, title: str) -> None: ...
    def remove(self, identifier: str | int) -> None: ...
    def marks(self) -> Iterable[Bookmark]: ...
    def to_string(self) -> str:
        """Serialize as 'HH:MM:SS.mmm,Title' lines."""
```

---

### Video

```python
# domain/video/stream_info.py
@dataclass(frozen=True, slots=True)
class VideoStreamInfo:
    codec: str
    width: int
    height: int
    fps: float
    bit_depth: int

@dataclass(frozen=True, slots=True)
class AudioStreamInfo:
    codec: str
    channels: int
    sample_rate: int

# domain/video/video_file.py
@dataclass(frozen=True, slots=True)
class VideoFile:
    """Core domain object representing a video file."""
    path: Path
    container_format: str           # "mp4", "mkv", "mov", etc.
    runtime: timedelta
    video_streams: tuple[VideoStreamInfo, ...]
    audio_streams: tuple[AudioStreamInfo, ...]
    chapters: VideoMarksFile | None
    tags: tuple[str, ...]
    storage_backend: StorageBackend
```

---

### Readers

```python
# domain/readers/chapters_file_reader.py
class ChaptersFileReader:
    """Reads '[HH:MM:SS.mmm] Title' text files into ChaptersFile."""
    def read(self, file_path: Path) -> Result[ChaptersFile]: ...

# domain/readers/bookmarks_file_reader.py
class BookmarksFileReader:
    """Reads 'HH:MM:SS.mmm,Title' text files into BookmarksFile."""
    def read(self, file_path: Path) -> Result[BookmarksFile]: ...

# domain/readers/videofile_reader.py
class VideofileReader:
    """Reads embedded chapters and stream tracks from a video file via ffprobe."""
    def read_chapters(self, path: Path) -> Result[ChaptersFile]: ...
    def read_streams(self, path: Path) -> Result[tuple[VideoStreamInfo, ...]]: ...

# domain/readers/videofile_metadata_reader.py
class VideofileMetadataReader:
    """Reads full video file metadata (streams + format + chapters + tags) via ffprobe."""
    def read(self, path: Path) -> Result[VideoFile]: ...
```

---

### Writers

```python
# domain/writers/chapter_write_strategy.py
class ChapterWriteStrategy(Protocol):
    """Writes chapters to a video file."""
    def write(self, video_path: Path, chapters: VideoMarksFile) -> Result[None]: ...

# domain/writers/mp4_chapters_writer.py
@dataclass
class MP4ChaptersWriter:
    """Embeds chapters in-place into an MP4 file via MP4Box."""
    def write(self, video_path: Path, chapters: VideoMarksFile) -> Result[None]: ...

# domain/writers/xattr_chapters_writer.py
@dataclass
class XattrChaptersWriter:
    """Writes serialized chapters to a file's extended attributes."""
    def write(self, video_path: Path, chapters: VideoMarksFile) -> Result[None]: ...
```

---

### Tagging

```python
# domain/tagging/tag_backend.py
@dataclass(slots=True)
class TagResult:
    tags: list[str]
    errors: list[str]

@dataclass(slots=True)
class TagWriteResult:
    success: bool
    errors: list[str]

class TagBackend(Protocol):
    def read_tags(self, path: Path) -> TagResult: ...
    def write_tags(self, path: Path, tags: list[str]) -> TagWriteResult: ...
    def add_tag(self, path: Path, tag: str) -> TagWriteResult: ...
    def remove_tag(self, path: Path, tag: str) -> TagWriteResult: ...

# domain/tagging/finder.py
@dataclass
class FinderTagBackend:
    """Reads/writes macOS Finder tags via xattr or CLI fallback."""
    def read_tags(self, path: Path) -> TagResult: ...
    def write_tags(self, path: Path, tags: list[str]) -> TagWriteResult: ...
    def add_tag(self, path: Path, tag: str) -> TagWriteResult: ...
    def remove_tag(self, path: Path, tag: str) -> TagWriteResult: ...
```

---

### Storage

```python
# domain/storage/storage_backend.py
class StorageBackend(Protocol):
    """Abstraction over file system access (local, SMB, AFP, etc.)."""
    def exists(self, path: Path) -> bool: ...
    def read_bytes(self, path: Path) -> bytes: ...
    def write_bytes(self, path: Path, data: bytes) -> None: ...
    def list_files(self, path: Path, extensions: frozenset[str]) -> list[Path]: ...
    def move(self, src: Path, dst: Path) -> None: ...
    def delete(self, path: Path) -> None: ...

# domain/storage/local.py
@dataclass
class LocalBackend:
    """Local filesystem implementation."""
    def exists(self, path: Path) -> bool: ...
    def read_bytes(self, path: Path) -> bytes: ...
    ...

# domain/storage/smb.py
@dataclass
class SMBBackend:
    """SMB/CIFS share access."""
    host: str
    share: str
    username: str
    password: str
    ...

# domain/storage/afp.py
@dataclass
class AFPBackend:
    """AFP share access (macOS-native mounted volumes)."""
    mount_path: Path
    ...
```

---

### Shared Infrastructure

```python
# domain/shared/result.py
@dataclass
class Result(Generic[T]):
    """Errors as values — no silent swallowing, no bare raises."""
    data: T | None = None
    errors: list[str] = field(default_factory=list)
    partial: bool = False

    def ok(self) -> bool:
        return self.data is not None and not self.errors

# domain/shared/command_runner.py
@dataclass(frozen=True, slots=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int

    def ok(self) -> bool:
        return self.returncode == 0

@dataclass
class CommandRunner:
    """Thin subprocess wrapper. Shared across all commands."""
    def run(
        self,
        args: Sequence[str],
        *,
        capture_output: bool = True,
        timeout: int | None = None,
    ) -> CommandResult: ...

# domain/shared/file_collector.py
@dataclass
class FileCollector:
    """Collect files matching extension criteria. Shared across all commands."""
    storage: StorageBackend

    def collect(
        self,
        root: Path,
        extensions: frozenset[str],
        recursive: bool = False,
    ) -> list[Path]: ...

# domain/shared/timecode.py
def parse_timecode(value: str) -> timedelta: ...
def format_timecode(delta: timedelta) -> str: ...
```

---

### Commands

#### chapterize

```python
# commands/chapterize/config.py
@dataclass(frozen=True)
class ChapterizeConfig:
    paths: tuple[Path, ...]
    chapters_dir: Path
    bookmarks_dir: Path
    video_roots: tuple[Path, ...]
    force: bool = False
    non_interactive: bool = False

# commands/chapterize/orchestrator.py
@dataclass
class ChapterizeOrchestrator:
    discovery: VideoDiscovery
    chapters_reader: ChaptersFileReader
    bookmarks_reader: BookmarksFileReader
    videofile_reader: VideofileReader
    merger: ChapterMerger
    resolver: ConflictResolver
    writer: ChapterWriteStrategy
    remux_service: FormatService     # injected; used only when video is MKV

    def run(self, config: ChapterizeConfig) -> Result[ChapterizeResult]: ...

# commands/chapterize/discovery.py
@dataclass
class VideoDiscovery:
    """Match video files to chapter/bookmark files by fuzzy name."""
    storage: StorageBackend

    def find_marks_for_video(self, video: Path) -> list[Path]: ...
    def find_videos_for_marks(self, marks_file: Path, roots: tuple[Path, ...]) -> list[Path]: ...

# commands/chapterize/merger.py
class ChapterMerger:
    """Merge two VideoMarksFile collections."""
    def merge(self, existing: VideoMarksFile, incoming: VideoMarksFile) -> VideoMarksFile: ...

# commands/chapterize/resolver.py
class ConflictResolver:
    """Decide keep / replace / merge when chapters already exist."""
    def resolve(
        self,
        existing: VideoMarksFile,
        incoming: VideoMarksFile,
        force: bool,
        non_interactive: bool,
    ) -> VideoMarksFile: ...
```

#### remux

```python
# commands/remux/orchestrator.py
@dataclass
class RemuxOrchestrator:
    collector: FileCollector
    format_service: FormatService    # injected (MP4Service, MKVService, etc.)

    def run(self, config: RemuxConfig) -> Result[RemuxResult]: ...

# commands/remux/mp4/service.py
class FormatService(Protocol):
    def remux(self, input_path: Path, output_path: Path | None) -> Result[Path]: ...

@dataclass
class MP4Service:
    """Remux input video into MP4 via ffmpeg stream copy."""
    runner: CommandRunner
    policy: MP4CompatibilityPolicy

    def remux(self, input_path: Path, output_path: Path | None) -> Result[Path]: ...

# commands/remux/mp4/policy.py
@dataclass(frozen=True)
class MP4CompatibilityPolicy:
    compatible_video_codecs: frozenset[str]
    compatible_audio_codecs: frozenset[str]

    def check(self, streams: tuple[VideoStreamInfo, ...]) -> CompatibilityReport: ...

# commands/remux/mp4/config.py
@dataclass(frozen=True)
class MP4Config:
    dry_run: bool = False
    verbose: bool = False
    log_file: Path | None = None
    max_workers: int | None = None
```

---

## Dependency Graph

```
CLI layer (commands/)
  │
  ├─ ChapterizeOrchestrator
  │     ├─ VideoDiscovery            ← StorageBackend
  │     ├─ ChaptersFileReader        ← domain/readers
  │     ├─ BookmarksFileReader       ← domain/readers
  │     ├─ VideofileReader           ← ffprobe, CommandRunner
  │     ├─ ChapterMerger             ← domain/videomarks
  │     ├─ ConflictResolver          ← domain/videomarks
  │     ├─ MP4ChaptersWriter         ← MP4Box, CommandRunner
  │     └─ MP4Service                ← ffmpeg, CommandRunner
  │
  └─ RemuxOrchestrator
        ├─ FileCollector             ← StorageBackend
        └─ MP4Service                ← ffmpeg, CommandRunner

Domain layer (domain/)
  │
  ├─ VideoFile                       (core domain object)
  ├─ ChaptersFile / BookmarksFile    (mark collections)
  ├─ VideofileMetadataReader         (ffprobe → VideoFile)
  ├─ FinderTagBackend                (xattr tags)
  └─ Result[T]                       (shared error container)

Shared infrastructure (domain/shared/)
  ├─ CommandRunner                   (subprocess)
  ├─ FileCollector                   (filesystem traversal)
  └─ timecode.py                     (pure functions)

Storage layer (domain/storage/)
  ├─ LocalBackend
  ├─ SMBBackend
  └─ AFPBackend
```

---

## Error Handling Policy

- **All readers** return `Result[T]`. No exceptions propagate to callers.
- **All writers** return `Result[None]`. Failures recorded as errors in Result.
- **CommandRunner** returns `CommandResult`. Callers inspect `returncode`.
- **Orchestrators** aggregate errors across all operations and return a final `Result`.
- **CLI layer** converts `Result` to exit codes and user-facing messages.

No silent swallowing (`except: pass`). No bare `raise`. Errors are data.

---

## Storage Protocol Design

Commands never call `open()`, `Path.read_text()`, or `os.path` directly. All file
operations go through `StorageBackend`. This makes SMB and AFP transparent to commands.

```
chapterize /Volumes/Zetc/video.mp4
  → LocalBackend detects /Volumes is a mounted volume
  → Reads chapters file via LocalBackend
  → Writes chapters via LocalBackend (which calls MP4Box)

# Future:
chapterize smb://nas/Zetc/video.mp4
  → SMBBackend handles path translation + file access
  → Command code is unchanged
```

SMBBackend and AFPBackend are **Phase 2** — the abstraction is built now, the
concrete implementations come later. Commands code against the protocol only.
