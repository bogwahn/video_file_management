# Current Codebase Analysis → New Structure Mapping

## DOMAIN LAYER

### VideoMarks Domain

#### Current: `marks/models.py` → **NEW: `domain/videomarks/videomark.py`**

```python
@dataclass(frozen=True, slots=True)
class VideoMark:
    timecode: timedelta
    label: str
```

**Analysis:**
- ✅ Correct: frozen + slots (immutable, memory efficient)
- ✅ Implements protocol concept (can be subclassed by Chapter, Bookmark)
- **Issue:** Should be a Protocol itself, not concrete class
- **Action:** Convert to Protocol; create Chapter and Bookmark concrete implementations

---

#### Current: `marks/protocols.py` → **NEW: `domain/videomarks/videomarks_file.py`**

```python
class VideoMarksFile(Protocol):
    file_path: str
    def add(self, timecode: str, label: str) -> None: ...
    def remove(self, identifier: str | int) -> None: ...
    def marks(self) -> Iterable[VideoMark]: ...
    def to_string(self) -> str: ...
```

**Analysis:**
- ✅ Good: Protocol-based abstraction
- ✅ Clear interface
- **Action:** Keep as-is; rename to `VideoMarksFile` protocol

---

#### Current: `marks/chapters_file.py` → **NEW: `domain/videomarks/chapters_file.py`**

```python
class ChaptersFile(VideoMarksFile):
    _marks: List[VideoMark]
    def add(self, timecode: str, label: str) -> None:
    def remove(self, identifier: str | int) -> None:
    def marks(self) -> Iterable[VideoMark]:
    def to_string(self) -> str:
```

**Analysis:**
- ✅ Correct: Implements VideoMarksFile protocol
- ✅ Serializes as `[HH:MM:SS.mmm] Label`
- **Issue:** Type hint uses `List` instead of `list` (Python 3.9+ should use `list`)
- **Issue:** No `BookmarksFile` equivalent (only BookmarksFileReader exists)
- **Action:** Update type hints to modern Python; create BookmarksFile implementation

---

#### NEW: `domain/videomarks/chapter.py` (Missing)

**Should implement:**
```python
@dataclass(frozen=True, slots=True)
class Chapter(VideoMark):
    """A VideoMark representing a chapter in a video."""
    pass
```

---

#### NEW: `domain/videomarks/bookmark.py` (Missing)

**Should implement:**
```python
@dataclass(frozen=True, slots=True)
class Bookmark(VideoMark):
    """A VideoMark representing a bookmark in a video."""
    pass
```

---

### Utility: Timecode

#### Current: `utils/timecode.py` → **NEW: `domain/timecode.py`** (or stays in utils/)

```python
def parse_timecode(value: str) -> timedelta:
def format_timecode(delta: timedelta) -> str:
```

**Analysis:**
- ✅ Correct: Pure functions, no state
- ✅ PEP 8 compliant
- ✅ Used across domain
- **Recommendation:** Move to `domain/` (shared across all commands), not `utils/`

---

### Tagging Domain

#### Current: `tag_reader.py` → **NEW: `domain/tagging/finder.py`**

```python
@dataclass(slots=True)
class TagReadResult:
    tags: List[str]
    errors: List[str]

def read_finder_tags(path: Path) -> TagReadResult:
```

**Analysis:**
- ✅ Correct: Handles xattr + CLI fallback
- ✅ Non-throwing (graceful failures)
- **Issue:** Uses `List` instead of `list`
- **Issue:** Only handles Finder tags; no abstraction for other tag backends
- **Action:** Rename to `domain/tagging/finder.py`; create TagBackend protocol

---

#### NEW: `domain/tagging/tag_backend.py` (Protocol needed)

**Should define:**
```python
class TagBackend(Protocol):
    """Abstraction for tag reading/writing backends."""
    def read_tags(self, path: Path) -> TagReadResult: ...
    def write_tags(self, path: Path, tags: list[str]) -> TagWriteResult: ...

@dataclass(slots=True)
class FinderTagBackend:
    """Concrete Finder tag implementation."""
    def read_tags(self, path: Path) -> TagReadResult: ...
```

---

## READER LAYER (domain/readers/)

### Current Readers

#### Current: `marks/readers.py` → **NEW: `domain/readers/chapters_file_reader.py`**

```python
class ChaptersFileReader:
    def read(self, file_path: str) -> ChaptersFile:
```

**Analysis:**
- ✅ Correct: Parses `[HH:MM:SS.mmm] Label` format
- ✅ Non-throwing (graceful ignore of malformed lines)
- **Action:** Rename to `ChaptersFileReader`; move to `domain/readers/`

---

#### Current: `marks/bookmarks_reader.py` → **NEW: `domain/readers/bookmarks_file_reader.py`**

```python
class BookmarksFileReader:
    def read(self, file_path: str) -> ChaptersFile:  # ← WRONG: should return BookmarksFile
```

**Analysis:**
- ✅ Correct logic: Parses `HH:MM:SS.mmm,Label` format
- ❌ **BUG:** Returns `ChaptersFile` instead of `BookmarksFile`
- ❌ **Type confusion:** Treating bookmarks as chapters
- **Action:** Create `BookmarksFile` class; update to return it

---

#### Current: `chapter_reader.py` → **NEW: `domain/readers/videofile_reader.py`**

```python
@dataclass(slots=True)
class ChapterEntry:
    start_seconds: float
    title: str

@dataclass(slots=True)
class ChapterReadResult:
    chapters: List[ChapterEntry]
    errors: List[str]

def read_chapters(path: Path) -> ChapterReadResult:
```

**Analysis:**
- ✅ Correct: Uses ffprobe to extract embedded chapters
- ✅ Non-throwing (collects errors)
- **Issue:** Uses `List` instead of `list`
- **Issue:** Only reads chapters; name doesn't reflect "internal tracks" (could be audio/video streams too)
- **Recommendation:** Rename to `VideofileReader` since it reads internal video metadata/tracks

---

#### Current: `metadata_reader.py` → **NEW: `domain/readers/videofile_metadata_reader.py`**

```python
@dataclass(slots=True)
class VideoStreamInfo:
    width, height, fps, codec, bit_depth

@dataclass(slots=True)
class AudioStreamInfo:
    codec, channels, sample_rate

@dataclass(slots=True)
class FileMetadata:
    path, format_name, runtime_seconds
    video: VideoStreamInfo
    audio: AudioStreamInfo
    chapters: list[ChapterInfo]
    tags: list[str]
    errors: list[str]

def read_file_metadata(path: Path) -> FileMetadata:
```

**Analysis:**
- ✅ Correct: Comprehensive metadata extraction via ffprobe
- ✅ Includes chapters and tags
- **Issue:** Mixes concerns (metadata reading + chapter reading + tag reading)
- **Issue:** Uses `list[ChapterInfo]` for chapters; should use `VideoMarksFile` abstraction
- **Recommendation:** Extract into separate readers:
  - `VideofileMetadataReader` (audio/video stream info only)
  - Keep chapter extraction in `VideofileReader`
  - Keep tag extraction in tagging backend

---

## COMMAND LAYER

### Remux Command

#### Current: `remux/service.py` → **NEW: `commands/remux/`** (keep service, refactor classes)

**Current classes:**
```python
@dataclass(frozen=True)
class Remux2Mp4Config:       # ← RENAME to MP4Config
    input_path, output_path, recursive, dry_run, verbose, log_file, max_workers

@dataclass(frozen=True)
class RunResult:             # ← Keep as-is
    stdout, stderr, returncode

@dataclass
class CommandRunner:         # ← Move to shared `domain/command_runner.py`
    def run(...) -> RunResult

@dataclass(frozen=True)
class StreamInfo:            # ← Move to `domain/video/stream_info.py`
    index, codec_type, codec_name

@dataclass(frozen=True)
class CompatibilityReport:   # ← Move to `commands/remux/mp4_policy.py`
    incompatible: Tuple[StreamInfo, ...]

@dataclass
class InputCollector:        # ← Move to shared `domain/file_collection.py` (used by all commands)
    def collect(...) -> list[Path]
```

**Analysis:**
- **Architecture Issue:** All command infrastructure mixed in one file
- **Recommendation:** Decompose into:
  - `commands/remux/mp4_config.py` (MP4Config, replaces Remux2Mp4Config)
  - `commands/remux/mp4_policy.py` (compatibility rules)
  - `commands/remux/service.py` (RemuxService - orchestrator for MP4)
  - `domain/command_runner.py` (shared CommandRunner)
  - `domain/file_collection.py` (shared InputCollector)

---

#### Current: `remux/cli.py` → **NEW: `commands/remux/cli.py`** (refactor)

```python
def _build_parser() -> argparse.ArgumentParser
def main(argv: Optional[list[str]] = None) -> int
```

**Analysis:**
- ✅ Simple: Delegates to Remux2Mp4Service
- **Issue:** Imports from remux.service; should import from remux.py (orchestrator)
- **Action:** Keep as-is; update imports after refactor

---

#### Current: `remux/remux_quickaction.py` → **NEW: `commands/remux/quickaction.py`** (rename)

```python
def main(argv: Optional[list[str]] = None) -> int
```

**Analysis:**
- ✅ Correct: Thin wrapper for Finder integration
- **Action:** Keep as-is; rename to match symmetry pattern

---

### Chapterize Command

#### Current: `chapterize/cli.py` → **NEW: `commands/chapterize/cli.py`** (massive refactor needed)

**Current monolithic ChapterizeCommand (lines 546–698):**
- 8 injected dependencies
- 110-line `_process_one()` method
- Mixed concerns: discovery, conflict resolution, remuxing, writing

**Architecture Issues (from AUDIT_PHASE3.md):**
1. Conflates orchestration with business logic
2. Direct imports of Remux2Mp4Service (dependency inversion violation)
3. Hardcoded video roots and chapter directories
4. Monolithic _process_one() method

**Recommendation:** Decompose into:
- `commands/chapterize/cli.py` (entry point, argparse)
- `commands/chapterize/orchestrator.py` (ChapterizeOrchestrator - thin coordinator)
- `commands/chapterize/discovery.py` (PathMatchIndex, VideoLocator)
- `commands/chapterize/merge_service.py` (MergeService - chapter merging logic)
- `commands/chapterize/resolution_service.py` (conflict resolution)

---

## SHARED INFRASTRUCTURE (needed)

### Domain Layer Abstractions

#### NEW: `domain/command_runner.py`

```python
@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int

@dataclass
class CommandRunner:
    def run(args: Sequence[str], capture_output: bool, timeout: Optional[int]) -> CommandResult
```

**Used by:** remux (ffmpeg), reencode (ffmpeg), encode (ffmpeg), etc.

---

#### NEW: `domain/file_collection.py`

```python
@dataclass
class FileCollector:
    def collect(self, input_path: Optional[Path], recursive: bool, extensions: frozenset[str]) -> list[Path]
```

**Used by:** remux, reencode, encode, name, etc.

---

#### NEW: `domain/video/`

```python
videofile_metadata.py:
  - VideoStreamInfo
  - AudioStreamInfo
  - VideoFileMetadata (core domain object)

stream_info.py:
  - StreamInfo
  - CompatibilityReport
```

---

## SUMMARY TABLE

| File | Type | Current Location | New Location | Action | PEP 8 Issues |
|------|------|------------------|--------------|--------|-------------|
| `marks/models.py` | Protocol | marks/ | domain/videomarks/ | **Refactor:** Convert VideoMark to Protocol | None |
| `marks/protocols.py` | Protocol | marks/ | domain/videomarks/ | Keep as-is | None |
| `marks/chapters_file.py` | Class | marks/ | domain/videomarks/ | Keep + update type hints | `List` → `list` |
| (missing) | Class | N/A | domain/videomarks/chapter.py | **CREATE** | N/A |
| (missing) | Class | N/A | domain/videomarks/bookmark.py | **CREATE** | N/A |
| `marks/bookmarks_reader.py` | Class | marks/ | domain/readers/ | Move + fix return type | `List` → `list` |
| `marks/readers.py` | Class | marks/ | domain/readers/ | Move as-is | None |
| `marks/writers.py` | Classes | marks/ | domain/writers/ | Keep (used by commands) | None |
| `chapter_reader.py` | Function | root | domain/readers/ | Rename to VideofileReader | `List` → `list` |
| `metadata_reader.py` | Function | root | domain/readers/ | Rename to VideofileMetadataReader | None |
| `tag_reader.py` | Function | root | domain/tagging/ | Move as FinderTagBackend | `List` → `list` |
| `utils/timecode.py` | Functions | utils/ | domain/timecode.py | Move (shared domain) | None |
| `remux/service.py` | Classes | remux/ | commands/remux/ + domain/ | **Refactor:** Extract MP4Config, CommandRunner, StreamInfo, etc. | None |
| `remux/cli.py` | Function | remux/ | commands/remux/ | Keep + update imports | None |
| `remux/remux_quickaction.py` | Function | remux/ | commands/remux/ | Rename to quickaction.py | None |
| `chapterize/cli.py` | Classes | chapterize/ | commands/chapterize/ | **Massive refactor:** Extract services | None |

---

## FOLDER STRUCTURE (Post-Analysis)

```
src/video_file_management/
├── commands/                          # Command entry points + orchestration
│   ├── chapterize/
│   │   ├── __init__.py
│   │   ├── cli.py                    # Entry point (argparse)
│   │   ├── orchestrator.py           # ChapterizeOrchestrator (coordinator)
│   │   ├── discovery.py              # PathMatchIndex, VideoLocator
│   │   ├── merge_service.py          # Chapter merging logic
│   │   └── resolution_service.py     # Conflict resolution
│   ├── remux/
│   │   ├── __init__.py
│   │   ├── cli.py                    # Entry point (argparse)
│   │   ├── service.py                # RemuxService (orchestrator for MP4)
│   │   ├── mp4_config.py             # MP4Config (was Remux2Mp4Config)
│   │   ├── mp4_policy.py             # MP4 compatibility rules
│   │   ├── mp4_service.py            # MP4Service (format-specific)
│   │   └── quickaction.py            # Finder integration
│   ├── reencode/                     # (future)
│   ├── tag/                          # (future)
│   ├── info/                         # (future)
│   └── name/                         # (future)
│
├── domain/                            # Core domain models + readers
│   ├── __init__.py
│   ├── timecode.py                   # parse_timecode, format_timecode
│   ├── command_runner.py             # Shared CommandRunner + CommandResult
│   ├── file_collection.py            # Shared FileCollector
│   │
│   ├── videomarks/
│   │   ├── __init__.py
│   │   ├── videomark.py              # VideoMark (Protocol)
│   │   ├── chapter.py                # Chapter (impl)
│   │   ├── bookmark.py               # Bookmark (impl)
│   │   └── videomarks_file.py        # VideoMarksFile (Protocol)
│   │
│   ├── video/
│   │   ├── __init__.py
│   │   ├── stream_info.py            # VideoStreamInfo, AudioStreamInfo
│   │   ├── metadata.py               # VideoFileMetadata (core domain object)
│   │   └── compatibility.py          # CompatibilityReport (codec policy results)
│   │
│   ├── readers/
│   │   ├── __init__.py
│   │   ├── chapters_file_reader.py   # ChaptersFileReader
│   │   ├── bookmarks_file_reader.py  # BookmarksFileReader
│   │   ├── videofile_reader.py       # Read embedded chapters/tracks (ffprobe)
│   │   └── videofile_metadata_reader.py  # Codec/duration/resolution (ffprobe)
│   │
│   ├── writers/
│   │   ├── __init__.py
│   │   ├── chapter_writers.py        # MP4ChaptersWriter, ChapterMetadataWriter (refactored)
│   │   └── strategies/               # (future: write strategies)
│   │
│   └── tagging/
│       ├── __init__.py
│       ├── tag_backend.py            # TagBackend (Protocol)
│       └── finder.py                 # FinderTagBackend (xattr-based)
│
├── scripts/                           # (keep as-is for now)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/
├── deploy/                            # (keep as-is)
├── docs/                              # (keep as-is)
└── __init__.py
```

---

## NEXT STEPS

1. **Create missing domain classes:** Chapter, Bookmark, BookmarksFile
2. **Fix type hints:** `List` → `list` across all files (Python 3.9+)
3. **Refactor remux:** Extract MP4Config, CommandRunner, StreamInfo into domain/
4. **Refactor chapterize:** Extract services (discovery, merge, resolution) from monolithic cli.py
5. **Create shared infrastructure:** CommandRunner, FileCollector, VideoFileMetadata
6. **Create tagging abstraction:** TagBackend protocol + FinderTagBackend implementation
7. **Update imports** across all files

---

**Status:** Analysis complete. Ready for refactoring blueprint + implementation plan.
