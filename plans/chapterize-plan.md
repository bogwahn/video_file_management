# chapterize — Execution Plan

## Status

**Current Phase:** Refactoring procedural implementation to OO architecture

**Completed:**

- ✅ Working procedural implementation with batch processing
- ✅ Protocol-based `marks/` module with readers/writers
- ✅ Interactive batch prompts and conversion support

**In Progress:**

- 🔄 Refactor to object-oriented architecture with DI
- 🔄 Separate Controllers from Execution logic
- 🔄 Add comprehensive unit tests

## Overview

`chapterize` is a focused function/CLI that provides the ability to add chapters to a videofile by applying the contents
of a chapter or bookmark file. `chapterize` should handle the following scenarios:

- Given a filename and an available chapters/bookmarks file, `chapterize` attaches a chapters track and reports a
summary message.
- Given a list of video filenames, a corresponding chapter file or bookmark file will be searched for each video. If
found, the chapters will be embedded and reports an aggregate summary message.

## Requirements

- Code must be in Python 3.14 or later.
- Must be organized and designed as an object oriented module with clear separation of concerns.
- Controllers should orchestrate the flow of data and handle user interactions
- Execution objects should focus on the core logic of chapterizing files.
- Execution objects should be designed to be reusable and testable, with clear input/output interfaces.
- Unit tests should be written for all components, with a focus on testing the execution logic in isolation from the CLI
and user interactions.
- Follow the principles of object-oriented design, including but not limited to:
  1. Favor composition over inheritance
  2. Program to a protocol, not an implementation
  3. Objects should be open for extension but closed for modification (Open/Closed Principle)
  4. Single Responsibility Principle: Each class should have only one reason to change, meaning it should have only one
  job or responsibility.
  5. Dependency Inversion Principle: High-level modules should not depend on low-level modules. Both should depend on
  protocols and ABCs (Abstract Base Classes). If an ABC is determined to be useful, it should implement a protocol.
  If no protocol exists, create it.
  6. Liskov Substitution Principle: Children of a superclass and classes implementing protocols should be replaceable
   with objects of a sub or implementing class without affecting the correctness of the program.
  7. Interface Segregation Principle: Clients should not be forced to depend on interfaces they do not use.
  8. Use dependency injection to manage dependencies between classes.
  9. **When runtime decisions are needed, inject creational patterns (factories, builders) via DI**

## Success Criteria

- Given a video filename and an available chapters/bookmarks file, `chapterize` attaches a chapters track and reports a summary message.
- Given a list of video files, chapters are embedded for each file with available chapters/bookmarks
- Returns structured results (success/failure/skipped) with clear summary reporting
- Returns a non-zero exit code and a clear message if no chapters/bookmarks files are supplied or found.
- Architecture follows OO principles with clear Controller/Service separation
- Dependencies injected via constructors; factories handle runtime decisions
- Comprehensive unit tests covering all components and edge cases

## Scope

- Command-line interface and library API that processes one or more files
- Reuses parsers and embedding helpers from `marks/` module
- Must not contain business logic in the CLI layer—only orchestration
- Follows existing project patterns in `remux2mp4` and `chapter_file_walker`

## Tasks

### Phase 1: Define Protocols and Models

1. Create result models: `ChapterizeResult`, `ProcessingStatus` (enum: Success, Failed, Skipped)
2. Define protocols:
   - `ChaptersLocator` - finds chapters files for videos
   - `VideoConverter` - converts non-MP4 formats
   - `ChaptersEmbedder` - embeds chapters into video files
   - `ChaptersReaderFactory` - creates appropriate reader based on file type

### Phase 2: Implement Core Services

1. Implement `ChaptersLocatorService` (wraps current `find_chapters_file_for`)
2. Implement `VideoConverterService` (wraps current `convert_to_mp4`)  
3. Implement `ChaptersEmbedderService` (orchestrates reader selection + writer)
4. Implement `ChaptersReaderFactory` for runtime reader selection

### Phase 3: Build Controller Layer

1. Implement `ChapterizeController`:
   - Accepts services via DI
   - Orchestrates: locate → convert (if needed) → embed
   - Returns structured `ChapterizeResult` objects
   - No direct subprocess calls or business logic
2. Implement batch processing with queue semantics
3. Add interactive prompt handler (separate concern)

### Phase 4: CLI and Integration

1. Refactor `main()` to wire dependencies and delegate to controller
2. Add `chapterize` entry point to `pyproject.toml`
3. Create composition root for DI container setup

### Phase 5: Testing

1. Write unit tests for each service (with mocks)
2. Write unit tests for controller (with test doubles)
3. Write integration tests for CLI
4. Write tests for result aggregation and reporting

## Example CLI

```bash
# Single file (auto-locates chapters file)
chapterize video1.mp4

# Multiple files
chapterize video1.mp4 video2.mov --dry-run

# Directory processing
chapterize --directory /path/to/videos

# With options
chapterize video1.mp4 --queue-size 50 --test-mode --non-interactive
```

## Estimates

- **Phase 1 (Protocols/Models):** 2-3 hours
- **Phase 2 (Services):** 4-6 hours  
- **Phase 3 (Controller):** 4-5 hours
- **Phase 4 (CLI):** 2-3 hours
- **Phase 5 (Testing):** 6-8 hours

**Total:** 2-3 days

## Next Steps

1. Review and approve this updated plan
2. Start with Phase 1: Define protocols and result models
3. Create a feature branch for the refactoring work
4. Implement incrementally with tests at each phase

## Queueing, conversion and test-mode (applies to CLI)

When used as a CLI or library for batch operations, `chapterize` should support the same priority and conversion semantics as the walker/service:

- Process MP4/MOV files immediately for embedding; queue non-MP4 files for conversion to MP4 first.
- Support a `--queue-size` option (default `100`) to control batching.
- Provide an interactive prompt after each batch: `continue`, `quit`, or `finish`. Add `--non-interactive` for scripted runs.
- Provide `--test-mode` to limit processing to `10` files for safe testing.

These flags make `chapterize` a safe building block for automated and interactive workflows.

## Architectural Design

### Component Structure

```text
┌────────────────────────────────────────┐
│           CLI Layer (main)             │
│  - Argument parsing                    │
│  - Dependency wiring (composition root)│
│  - Result formatting & exit codes      │
└────────────┬───────────────────────────┘
             │
             ▼
┌────────────────────────────────────────┐
│      ChapterizeController              │
│  - Orchestrates workflow               │
│  - Batch management                    │
│  - Progress reporting                  │
└────────────┬───────────────────────────┘
             │
             │  Injected Dependencies
             ├──────────────────────────┐
             │                          │
             ▼                          ▼
┌─────────────────────┐   ┌──────────────────────┐
│ ChaptersLocator     │   │ ChaptersEmbedder     │
│  (service)          │   │  (service)           │
└─────────────────────┘   └──────────┬───────────┘
                                     │
             ┌───────────────────────┴────────────┐
             ▼                                    ▼
┌──────────────────────┐            ┌──────────────────────┐
│ VideoConverter       │            │ ChaptersReaderFactory│
│  (service)           │            │  (factory - DI)      │
└──────────────────────┘            └──────────┬───────────┘
                                               │
                                     ┌─────────┴─────────┐
                                     ▼                   ▼
                        ┌───────────────────┐ ┌──────────────────┐
                        │ChaptersFileReader │ │BookmarksFileReader│
                        └───────────────────┘ └──────────────────┘
```

### Key Principles in Design

1. **Controller has no business logic** — only orchestration
2. **Services injected via constructor** — testable with mocks
3. **Factory injected for runtime decisions** — determines reader type based on file extension
4. **Protocols define contracts** — implementations can vary
5. **Results flow up** — structured data, not side effects

### Example Wiring (Composition Root)

```python
def create_controller() -> ChapterizeController:
    # Create concrete services
    locator = ChaptersLocatorService(DEFAULT_CHAPTERS_DIR)
    converter = VideoConverterService()
    reader_factory = ChaptersReaderFactory()
    writer = MP4ChaptersWriter()
    
    # Inject factory into embedder
    embedder = ChaptersEmbedderService(
        reader_factory=reader_factory,
        writer=writer
    )
    
    # Inject all into controller
    return ChapterizeController(
        locator=locator,
        converter=converter,
        embedder=embedder
    )
```

This design ensures:

- ✅ Dependencies are explicit and testable
- ✅ Runtime decisions (reader selection) use injected factories
- ✅ Each class has a single, clear responsibility
- ✅ Easy to swap implementations via protocols
