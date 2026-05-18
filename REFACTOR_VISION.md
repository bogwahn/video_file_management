# Phase 3 Refactoring End State

## Project Structure (Post-Refactor)

```
src/video_file_management/
├── __init__.py
├── chapterize/
│   ├── __init__.py
│   ├── cli.py                          # Argparse entry point → orchestrator
│   ├── quickaction.py                  # NEW: Finder Quick Action wrapper
│   ├── orchestrator.py                 # NEW: ChapterizeOrchestrator (thin coordinator)
│   ├── matching_service.py             # NEW: PathMatchIndex + VideoLocator
│   ├── preparation_service.py          # NEW: VideoPreparationStrategy impl
│   ├── resolution_service.py           # NEW: Conflict resolution logic
│   ├── metadata_reader.py              # Renamed: chapterize/metadata_reader.py
│   └── models.py                       # ChapterizeRequest, ChapterizeResult (NEW)
│
├── remux/
│   ├── __init__.py
│   ├── cli.py                          # Argparse entry point
│   ├── quickaction.py                  # Finder Quick Action wrapper (existing)
│   ├── service.py                      # Remux2Mp4Service
│   └── models.py                       # RemuxRequest, RemuxResult (NEW)
│
├── marks/
│   ├── __init__.py
│   ├── models.py                       # VideoMark, VideoMarksFile protocol
│   ├── readers.py                      # read_chapters_file(), read_bookmarks_file()
│   ├── writers.py                      # REFACTORED: Strategy pattern
│   │                                   # - MP4ChaptersWriter (factory/coordinator)
│   │                                   # - ChapterWriteStrategy (protocol)
│   │                                   # - InPlaceChapterWriter (strategy impl)
│   │                                   # - CopyToNewChapterWriter (strategy impl)
│   └── [legacy]
│       ├── bookmarks_reader.py         # Deprecated (calls new read_bookmarks_file)
│       └── ffmpeg_writer.py            # Deprecated (logic moved to writers.py)
│
├── metadata_reader.py                  # REFACTORED: Metadata extraction coordination
│                                       # - read_file_metadata() coordinates extractors
│                                       # - VideoMetadataExtractor
│                                       # - ChapterMetadataExtractor (NEW)
│
├── metadata/                           # NEW: Extracted metadata extraction logic
│   ├── __init__.py
│   ├── extractors.py                   # VideoMetadataExtractor, AudioMetadataExtractor, etc.
│   ├── protocols.py                    # MetadataExtractor protocol
│   └── models.py                       # VideoMetadata, AudioMetadata dataclasses
│
├── config/                             # NEW: Configuration management
│   ├── __init__.py
│   ├── directory_config.py             # DirectoryConfiguration dataclass
│   └── strategies.py                   # VideoPreparationStrategy protocol
│
├── utils/
│   ├── __init__.py
│   ├── timecode.py                     # parse_timecode, format_timecode
│   ├── path_helpers.py                 # Path utilities
│   └── io_helpers.py                   # I/O utilities
│
└── chapter_reader.py                   # (existing, unchanged)
```

---

## Key Object Models & Protocols

### 1. Chapterize Command Pipeline

```python
# src/video_file_management/chapterize/models.py

@dataclass
class ChapterizeRequest:
    """Input to chapterize operation."""
    video_paths: list[Path]
    non_interactive: bool = False
    force: bool = False

@dataclass
class ChapterizeResult:
    """Output from chapterize operation."""
    successes: list[Path]
    failures: dict[Path, str]  # path → error message
    skipped: list[Path]
    merged_count: int = 0
```

### 2. Orchestrator Pattern (Replaces Monolithic ChapterizeCommand)

```python
# src/video_file_management/chapterize/orchestrator.py

@dataclass
class ChapterizeOrchestrator:
    """Thin coordinator; delegates to specialized services."""
    matching_service: MatchingService
    preparation_service: VideoPreparationStrategy
    resolution_service: ResolutionService
    metadata_reader: MetadataReader  # (existing, unchanged)
    chapters_writer: MP4ChaptersWriter  # (existing, refactored)
    
    def process(self, request: ChapterizeRequest) -> ChapterizeResult:
        """Orchestrate the full chapterize flow."""
        # 1. Discover videos (→ MatchingService)
        videos = self.matching_service.find_videos(request.video_paths)
        
        # 2. Prepare videos if needed (→ PreparationService)
        prepared = [self.preparation_service.prepare(v) for v in videos]
        
        # 3. Resolve conflicts and write chapters (→ ResolutionService)
        result = ChapterizeResult(successes=[], failures={}, skipped=[])
        for video in prepared:
            try:
                chapters = self._load_chapters(video)
                resolved = self.resolution_service.resolve(
                    video, chapters, request.force, request.non_interactive
                )
                self.chapters_writer.write(video, resolved.chapters)
                result.successes.append(video)
            except Exception as e:
                result.failures[video] = str(e)
        
        return result
```

### 3. Extracted Services (Single Responsibility)

```python
# src/video_file_management/chapterize/matching_service.py

@dataclass
class MatchingService:
    """Owns video-to-marks discovery."""
    directory_config: DirectoryConfiguration  # INJECTED
    
    def find_videos(self, paths: list[Path]) -> list[Path]:
        """Find video files matching chapters/bookmarks."""
        locator = VideoLocator(self.directory_config)
        index = PathMatchIndex(locator, self.directory_config)
        return index.matched_videos(paths)


# src/video_file_management/chapterize/preparation_service.py

@dataclass
class DefaultRemuxPreparation:
    """VideoPreparationStrategy implementation."""
    remux_service: Remux2Mp4Service  # INJECTED
    
    def prepare(self, video_path: Path) -> Path:
        """Ensure video is MP4-compatible; remux if needed."""
        if self._is_compatible(video_path):
            return video_path
        return self.remux_service.remux(video_path)


# src/video_file_management/chapterize/resolution_service.py

@dataclass
class ResolutionService:
    """Owns conflict resolution logic."""
    merge_service: MergeService  # INJECTED
    
    def resolve(
        self,
        video: Path,
        new_chapters: VideoMarksFile,
        force: bool,
        non_interactive: bool
    ) -> ResolvedChapters:
        """Merge existing + new chapters; handle conflicts."""
        existing = self._read_existing(video)
        if force or not existing:
            return ResolvedChapters(new_chapters, conflict_count=0)
        
        merged = self.merge_service.merge(existing, new_chapters)
        # Handle conflicts (keep/replace/merge) based on flags
        return merged
```

### 4. Write Strategy Pattern (Replaces Dual-Mode write())

```python
# src/video_file_management/marks/writers.py

class ChapterWriteStrategy(Protocol):
    """Write chapters to video using a specific strategy."""
    def write(self, video_path: Path, chapters: VideoMarksFile) -> None: ...


@dataclass
class InPlaceChapterWriter:
    """Fast: embed chapters in-place (MP4Box only)."""
    def write(self, video_path: Path, chapters: VideoMarksFile) -> None:
        # ~20 lines: MP4Box -chap only
        ...


@dataclass
class CopyToNewChapterWriter:
    """Safe: create new file, verify, then atomic replace."""
    def write(self, video_path: Path, chapters: VideoMarksFile) -> None:
        # ~60 lines: ffmpeg remove + MP4Box -chap + atomic replace
        ...


@dataclass
class MP4ChaptersWriter:
    """Factory/coordinator: select strategy and write."""
    in_place_strategy: ChapterWriteStrategy
    copy_to_new_strategy: ChapterWriteStrategy
    
    def write(
        self,
        video_path: Path,
        chapters: VideoMarksFile,
        output_path: Optional[Path] = None
    ) -> None:
        """Choose strategy based on output_path."""
        strategy = (
            self.copy_to_new_strategy if output_path
            else self.in_place_strategy
        )
        strategy.write(video_path, chapters)
        if output_path:
            shutil.move(str(video_path), str(output_path))
```

### 5. Configuration & Dependency Injection

```python
# src/video_file_management/config/directory_config.py

@dataclass(frozen=True)
class DirectoryConfiguration:
    """Centralized directory configuration."""
    video_roots: tuple[Path, ...]
    chapters_dir: Path
    bookmarks_dir: Path
    
    @classmethod
    def from_env(cls) -> "DirectoryConfiguration":
        """Load from environment variables with sane defaults."""
        return cls(
            video_roots=tuple(
                Path(p) for p in os.getenv(
                    "VIDEO_ROOTS", str(Path.home() / "Videos")
                ).split(":")
            ),
            chapters_dir=Path(os.getenv(
                "CHAPTERS_DIR", str(Path.home() / ".chapters")
            )),
            bookmarks_dir=Path(os.getenv(
                "BOOKMARKS_DIR", str(Path.home() / ".bookmarks")
            )),
        )


# src/video_file_management/config/strategies.py

class VideoPreparationStrategy(Protocol):
    """Strategy for preparing videos for chapter embedding."""
    def prepare(self, video_path: Path) -> Path: ...
```

### 6. Metadata Extraction (Separated Concerns)

```python
# src/video_file_management/metadata/extractors.py

class MetadataExtractor(Protocol):
    """Extract a specific metadata type from ffprobe output."""
    def extract(self, ffprobe_data: dict) -> Optional[Any]: ...


@dataclass
class VideoMetadataExtractor:
    """Extract video stream metadata."""
    def extract(self, ffprobe_data: dict) -> Optional[VideoMetadata]:
        format_info = ffprobe_data.get("format", {})
        stream = next(
            (s for s in ffprobe_data.get("streams", [])
             if s["codec_type"] == "video"),
            None
        )
        if not stream:
            return None
        return VideoMetadata(
            codec=stream.get("codec_name"),
            duration=format_info.get("duration"),
        )


@dataclass
class ChapterMetadataExtractor:
    """Extract chapter metadata."""
    def extract(self, ffprobe_data: dict) -> list[ChapterInfo]:
        # Isolated, testable chapter extraction
        ...


# src/video_file_management/metadata_reader.py (refactored)

def read_file_metadata(
    video_path: Path,
    extractors: Optional[list[MetadataExtractor]] = None
) -> ParseResult[FileMetadata]:
    """Coordinate metadata extraction with multiple extractors."""
    if extractors is None:
        extractors = [
            VideoMetadataExtractor(),
            AudioMetadataExtractor(),
            ChapterMetadataExtractor(),
        ]
    
    # Run ffprobe once
    ffprobe_data = run_ffprobe(video_path)
    
    # Delegate to extractors
    result = ParseResult(data=FileMetadata())
    for extractor in extractors:
        try:
            extracted = extractor.extract(ffprobe_data)
            if extracted:
                result.data.add_metadata(extracted)
        except Exception as e:
            result.errors.append(f"{extractor.__class__.__name__}: {e}")
            result.partial = True
    
    return result
```

### 7. Consistent Error Handling Pattern

```python
# src/video_file_management/utils/result.py

@dataclass
class ParseResult(Generic[T]):
    """Unified result type for parsing/extraction operations."""
    data: Optional[T] = None
    errors: list[str] = field(default_factory=list)
    partial: bool = False  # True if some parsing succeeded despite errors
    
    def is_success(self) -> bool:
        return self.data is not None and len(self.errors) == 0
    
    def is_partial(self) -> bool:
        return self.data is not None and len(self.errors) > 0


# Usage across readers/writers/extractors
def read_chapters_file(file_path: Path) -> ParseResult[VideoMarksFile]:
    result = ParseResult(data=VideoMarksFile())
    try:
        lines = file_path.read_text().splitlines()
        for i, line in enumerate(lines):
            try:
                mark = parse_chapter_line(line)
                result.data.add(mark)
            except ValueError as e:
                result.errors.append(f"Line {i}: {e}")
                result.partial = True
    except Exception as e:
        result.errors.append(f"File read failed: {e}")
    
    return result
```

---

## Architecture Diagram (Post-Refactor)

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
│  chapterize/cli.py  (argparse) → remux/cli.py              │
└────────────┬──────────────────────────────┬─────────────────┘
             │                              │
             ▼                              ▼
   ┌─────────────────────┐      ┌──────────────────────┐
   │ ChapterizeOrchestrator
   │ (thin coordinator)   │      │  Remux2Mp4Service   │
   │                      │      │  (existing)         │
   └────────┬─────────────┘      └──────────────────────┘
            │
    ┌───────┼───────┬──────────────┐
    │       │       │              │
    ▼       ▼       ▼              ▼
┌────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐
│Matching│ │Prep      │ │Resolution    │ │Chapters     │
│Service │ │Service   │ │Service       │ │Writer       │
│        │ │(DI: RemuxS) │(DI: Merge) │ │(Strategy)   │
└────────┘ └──────────┘ └──────────────┘ └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────┐
                    │                          │          │
                    ▼                          ▼          ▼
            ┌──────────────┐        ┌────────────────┐ ┌──────────┐
            │InPlace       │        │CopyToNew       │ │MP4Box    │
            │Writer        │        │Writer          │ │CLI       │
            └──────────────┘        └────────────────┘ └──────────┘

             ▼
    ┌─────────────────────┐
    │ Shared Infrastructure
    ├─────────────────────┤
    │ marks/              │
    │  - readers/writers  │  (refactored write strategy)
    │  - models           │
    │ metadata/           │
    │  - extractors       │  (separated concerns)
    │  - models           │
    │ config/             │  (dependency injection)
    │  - DirectoryConfig  │
    │  - Strategies       │
    │ utils/              │
    │  - timecode         │
    │  - result pattern   │  (ParseResult[T])
    └─────────────────────┘
```

---

## Benefits of End State

### ✅ Testability
- **Before:** Mock all 8 dependencies just to test discovery logic
- **After:** Test MatchingService in isolation; mock only PathMatchIndex

### ✅ Extensibility
- **Before:** Add new discovery strategy → modify ChapterizeCommand
- **After:** Implement MatchingService interface; inject it

### ✅ Clarity
- **Before:** _process_one() method does 6 different things (110 lines)
- **After:** Each service has clear, single responsibility

### ✅ Reusability
- **Before:** VideoMetadataExtractor logic mixed in read_file_metadata()
- **After:** Extractors are independently composable

### ✅ Configuration
- **Before:** Directory roots hardcoded in constants
- **After:** DirectoryConfiguration loaded from env/config; injectable

### ✅ Error Handling
- **Before:** Mixed patterns (silent ignore, append errors, raise exceptions)
- **After:** Consistent ParseResult[T] across all readers/parsers/writers

---

## File Changes Summary

| File | Current | After Phase 3 | Change |
|------|---------|---------------|--------|
| `chapterize/cli.py` | Monolithic ChapterizeCommand | Delegating orchestrator | Refactored |
| `chapterize/orchestrator.py` | N/A | NEW | New |
| `chapterize/matching_service.py` | N/A | NEW | New |
| `chapterize/preparation_service.py` | N/A | NEW | New |
| `chapterize/resolution_service.py` | N/A | NEW | New |
| `chapterize/quickaction.py` | N/A | NEW | New (symmetry with remux) |
| `marks/writers.py` | Dual-mode write() | Strategy pattern | Refactored |
| `marks/writers.py` + `metadata_reader.py` | Mixed extraction logic | Separate extractors | Refactored |
| `config/directory_config.py` | N/A | NEW | New (DI) |
| `metadata/extractors.py` | N/A | NEW | New (SoC) |
| `utils/result.py` | N/A | NEW | New (error pattern) |

---

## Refactor Effort Estimate

- **Phase 1:** Extract services from ChapterizeCommand (~2–3 days)
  - Create orchestrator, matching_service, preparation_service, resolution_service
  - Update cli.py to use orchestrator
  - Add unit tests for each service
  
- **Phase 2:** Fix write strategy + quickaction (~2–3 days)
  - Split MP4ChaptersWriter into strategies (InPlace, CopyToNew)
  - Create chapterize/quickaction.py
  - Add tests for strategies
  
- **Phase 3:** Polish + error handling (~3–4 days)
  - Extract metadata extractors (separated concerns)
  - Introduce ParseResult[T] pattern
  - Standardize reader/writer naming (deprecate old classes)
  - Comprehensive test coverage

**Total:** ~1–2 week focused refactoring sprint (TDD: write tests first per PROJECT_RULES)

---

**Status:** Refactoring design complete. Ready for Phase 3 implementation PR.
