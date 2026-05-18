# Code Quality Audit — Phase 3

**Status:** Complete  
**Date:** 2026-05-18  
**Scope:** ~12 surviving modules (chapterize, remux, marks, metadata_reader packages)  
**Focus:** SOLID violations, naming consistency, single-responsibility adherence

---

## EXECUTIVE SUMMARY

Audited all surviving code after Phase 1 & 2 cleanup. Found **8 significant issues** spanning **3 severity levels**:

- **1 HIGH:** `ChapterizeCommand` does too much; refactor needed to enable testing
- **4 MEDIUM:** Asymmetric package structure, interface segregation, dependency inversion, write mode branching
- **3 LOW:** Naming inconsistency, hardcoded policies, mixed error handling

**Total effort:** ~2 weeks of focused refactoring to address all issues.  
**Recommended approach:** Phase 1 (immediate) → Phase 2 (near-term) → Phase 3 (polish) → Deferred (nice-to-have).

---

## CRITICAL FINDINGS

### 1. SINGLE RESPONSIBILITY VIOLATION: `chapterize/cli.py` → ChapterizeCommand (HIGH)

**File:** `src/video_file_management/chapterize/cli.py` (lines 546–698)

**Issue:** The `ChapterizeCommand` class conflates orchestration, discovery, conflict resolution, and video preparation. The `_process_one()` method (110 lines, 6 conditional branches) mixes:
- Video-to-marks discovery (PathMatchIndex, VideoLocator)
- Marks merging (MergeService)
- CLI state management (force flag, prompt resolution)
- Atomic remux-on-demand (calls `_prepare_video_for_chapterize()`)

**Root Cause:**
- 8 injected dependencies + state flags
- No service abstraction layer
- `_process_one()` handles completely different concerns in one method

**Why It Matters:**
- **Testability:** Any test of discovery logic must mock all 8 dependencies
- **Extensibility:** Adding new discovery strategies requires modifying this class (Open/Closed violation)
- **Maintenance:** 110-line method with 6 branches is hard to reason about and error-prone

**Proposed Fix:**
Extract three new services:
- **MatchingService:** owns PathMatchIndex + VideoLocator (lines 600–617)
- **PreparationService:** owns remux logic (lines 629–640)
- **ResolutionService:** owns conflict handling

Rename `ChapterizeCommand` → `ChapterizeOrchestrator`; it becomes a thin coordinator delegating to services.

**Effort:** Medium (1–2 days)  
**Impact:** Enables unit testing of discovery, merging, and remux logic independently

---

### 2. ASYMMETRIC PACKAGE STRUCTURE (MEDIUM)

**Files:**
- `remux/remux_quickaction.py` exists (CLI wrapper for Finder Quick Actions)
- `chapterize/` has NO equivalent

**Issue:** Remux has a dedicated quickaction entry point; chapterize doesn't. This asymmetry suggests incomplete refactoring.

**Root Cause:** Remux was refactored recently to add quickaction support. Chapterize wasn't included.

**Why It Matters:**
- **Consistency:** Two equivalent features have different architectures
- **Maintenance:** Users expect chapterize to work in Quick Actions too
- **Discoverability:** Pattern is hidden in remux; next developer won't know where to find it

**Proposed Fix:**
Create `chapterize/quickaction.py` mirroring `remux/remux_quickaction.py`:
```python
def main(argv: Optional[list[str]] = None) -> int:
    # Thin wrapper around ChapterizeCommand for Finder integration
    ...
```

Add to `pyproject.toml` entry points. Consider moving both to a shared `quickactions/` subdirectory or creating a `QuickActionBase` mixin.

**Effort:** Low (2–4 hours)  
**Impact:** Symmetric design, consistent user experience

---

### 3. INTERFACE SEGREGATION VIOLATION: `marks/writers.py` → MP4ChaptersWriter.write() (MEDIUM)

**File:** `src/video_file_management/marks/writers.py` (lines 99–199)

**Issue:** The `write()` method has two radically different code paths:
- **In-place write** (output_path is None, ~20 lines): Fast path using MP4Box only
- **Copy-to-new write** (output_path provided, ~60 lines): Slow path using ffmpeg + MP4Box, 4 temp files

**Root Cause:** Single method handles two distinct use cases. The "mode" is implicit (None vs. a path).

**Why It Matters:**
- **Testability:** Testing requires setting up two completely different scenarios
- **Clarity:** Method signature doesn't signal behavioral difference (`output_path=None` is magical)
- **Extensibility:** Adding a third write strategy (streaming output, dry-run, etc.) requires modifying this class

**Proposed Fix:**
Create a **Strategy interface**:
```python
class ChapterWriteStrategy(Protocol):
    def write(self, src: Path, chapters: VideoMarksFile) -> None: ...
```

Implement two concrete strategies:
- `InPlaceChapterWriter` (lines 117–139 logic)
- `CopyToNewChapterWriter` (lines 141–199 logic)

Refactor `MP4ChaptersWriter.write()` to accept a strategy or auto-select based on output_path.

**Effort:** Medium (1–2 days)  
**Impact:** Testable, extensible write logic; easier to add new strategies later

---

### 4. INCONSISTENT NAMING: Reader/Writer Classes (LOW)

**Files:**
- `marks/bookmarks_reader.py`: `BookmarksFileReader`
- `marks/readers.py`: `ChaptersFileReader`
- `marks/writers.py`: `MP4ChaptersWriter`, `ChapterMetadataWriter`
- `metadata_reader.py`: `read_file_metadata()` (function)
- `chapter_reader.py`: `read_chapters()` (function)

**Issue:** Mixed naming patterns:
1. Class: `<Domain>FileReader` (BookmarksFileReader, ChaptersFileReader)
2. Class: `<Domain>ChaptersWriter` (MP4ChaptersWriter)
3. Function: `read_<domain>()` (read_file_metadata, read_chapters)

**Why It Matters:**
- **Discoverability:** New developers don't know whether to look for a class or function
- **API Surface:** Harder to learn and predict
- **Naming:** Different noun order in class names (ChaptersFile vs. ChapterMetadata)

**Proposed Fix:**
Standardize to **function-based readers/writers**:
```python
# marks/readers.py
def read_chapters_file(file_path: str) -> VideoMarksFile: ...
def read_bookmarks_file(file_path: str) -> VideoMarksFile: ...

# marks/writers.py
def write_chapters_to_mp4(video_path: str, chapters: VideoMarksFile) -> None: ...
def write_chapters_metadata(video_path: str, chapters: VideoMarksFile) -> None: ...
```

Keep class-based readers for backward compat (call functions internally).

**Effort:** Low (4–6 hours)  
**Impact:** Clearer, more predictable API surface

---

### 5. DEPENDENCY INVERSION VIOLATION: `chapterize/cli.py` → Direct Instantiation (MEDIUM)

**File:** `src/video_file_management/chapterize/cli.py` (lines 70–93, 549–570, 746–748)

**Issue:** `ChapterizeCommand` directly instantiates concrete implementations:
- Lines 70–93: `_prepare_video_for_chapterize()` hardcodes `Remux2Mp4Service()`
- Lines 600–617: PathMatchIndex hardcoded with directory constants
- Lines 746–748: Manual object graph construction with no inversion of control

**Root Cause:** No abstraction over "video preparation" or "directory configuration." Class depends on concrete implementations, not abstractions.

**Why It Matters:**
- **Testing:** Can't inject a mock remux service; tests must accept actual remux behavior
- **Flexibility:** Can't swap Remux2Mp4Service for alternatives (dry-run, logging wrapper, etc.)
- **Configuration:** Video roots and chapter dirs hardcoded in constants; env vars feel bolted on

**Proposed Fix:**
Create **VideoPreparationStrategy** protocol:
```python
class VideoPreparationStrategy(Protocol):
    def prepare(self, video_path: Path) -> Path: ...
```
Implement `DefaultRemuxPreparation` wrapping Remux2Mp4Service. Inject into ChapterizeOrchestrator.

Create **DirectoryConfiguration** dataclass:
```python
@dataclass
class DirectoryConfiguration:
    video_roots: tuple[Path, ...]
    chapters_dir: Path
    bookmarks_dir: Path
```
Load from env or config file; pass to PathMatchIndex instead of building inline.

**Effort:** Medium (1–2 days)  
**Impact:** Testable orchestration, swappable strategies, externalized configuration

---

## MEDIUM/LOW PRIORITY FINDINGS

### 6. OPEN/CLOSED PRINCIPLE VIOLATION: `remux/service.py` → Codec Policies (LOW)

**File:** `src/video_file_management/remux/service.py` (lines 155–175)

**Issue:** `Mp4CompatibilityPolicy` hardcodes codec allowlists. To add a new codec or container format, modify the class.

**Proposed Fix:** Load codec policies from config file or environment; or inject a PolicyProvider.

**Effort:** Low | **Impact:** Extensibility for new codecs

---

### 7. WEAK SEPARATION OF CONCERNS: `metadata_reader.py` (LOW)

**File:** `src/video_file_management/metadata_reader.py` (lines 150–191)

**Issue:** `read_file_metadata()` mixes ffprobe invocation, format parsing, video stream parsing, audio parsing, chapter extraction, and Finder tag reading.

**Proposed Fix:** Extract `VideoMetadataExtractor`, `ChapterMetadataExtractor`, etc. classes that parse independently from ffprobe invocation.

**Effort:** Medium | **Impact:** Reusable parsers, independent testing

---

### 8. INCONSISTENT ERROR HANDLING (LOW)

**Files:** `marks/readers.py`, `chapter_reader.py`, `metadata_reader.py`, `remux/service.py`

**Issue:** No consistent pattern:
- Readers silently skip malformed entries
- Metadata readers append errors to result objects
- Service classes raise exceptions or return status fields

**Proposed Fix:** Create `ParseResult[T]` generic for all readers/parsers to return consistently.

**Effort:** Medium | **Impact:** Predictable error propagation

---

## SUMMARY TABLE

| # | Issue | File | Lines | Principle | Priority | Effort |
|----|-------|------|-------|-----------|----------|--------|
| 1 | ChapterizeCommand does too much | `chapterize/cli.py` | 546–698 | SRP | **HIGH** | Medium |
| 2 | Remux has quickaction, chapterize doesn't | `chapterize/`, `remux/` | N/A | SRP | **MEDIUM** | Low |
| 3 | MP4ChaptersWriter has two write modes | `marks/writers.py` | 99–199 | ISP | **MEDIUM** | Medium |
| 4 | Reader/Writer naming inconsistent | `marks/*`, `metadata_reader.py` | Multiple | Naming | **LOW** | Low |
| 5 | ChapterizeCommand depends on concrete services | `chapterize/cli.py` | 70–93, 549–570 | DIP | **MEDIUM** | Medium |
| 6 | Codec policies hardcoded | `remux/service.py` | 155–175 | OCP | **LOW** | Low |
| 7 | Metadata reader mixes concerns | `metadata_reader.py` | 150–191 | SRP | **LOW** | Medium |
| 8 | Error handling inconsistent | Multiple | Multiple | Pattern | **LOW** | Medium |

---

## RECOMMENDED REFACTOR ROADMAP

### Phase 1 — Immediate (Unblocks Testing)
- Issue #1: Extract services from ChapterizeCommand
- Issue #5: Introduce dependency injection for video preparation

**Effort:** ~2–3 days | **Impact:** High — enables unit testing and extensibility

### Phase 2 — Near-term (Consistency)
- Issue #2: Add chapterize quickaction
- Issue #3: Split MP4ChaptersWriter into strategies

**Effort:** ~2–3 days | **Impact:** Symmetric design, cleaner write logic

### Phase 3 — Polish (API Clarity)
- Issue #4: Standardize reader/writer names
- Issue #8: Introduce ParseResult pattern for error handling

**Effort:** ~3–4 days | **Impact:** Clearer API surface, consistent error propagation

### Deferred (Nice-to-have)
- Issue #6: Extract codec policies to config
- Issue #7: Extract metadata extractors

**Effort:** ~2–3 days | **Impact:** Low immediate value; revisit later

---

## NEXT STEPS

1. **Create a refactor PR** addressing Phase 1 + Phase 2 issues (1–2 week sprint)
2. **Keep main stable** — no feature work during refactoring
3. **Add tests** as services are extracted (per TDD mandate in PROJECT_RULES)
4. **Polish** with Phase 3 after refactor is committed

---

**Document created:** 2026-05-18  
**Ready for:** Phase 3 refactoring (planned as separate PR)
