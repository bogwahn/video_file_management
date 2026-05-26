# chapterize — CLI Design and Execution Plan

## Purpose

Build and maintain a componentized CLI command `chapterize` that processes zero-or-more file and directory inputs, resolves video/marks relationships, and writes chapters with explicit user conflict resolution.

This plan is CLI-only and does not depend on macOS UI dialogs.

## Non-Negotiable Constraints

### 1) Allowed Video Search Roots (Only)

The command may search for corresponding video files only under these roots:

- /Volumes/Zetc/Models
- /Volumes/Zetc/Studios
- /Volumes/Zetc/Uncategorized
- /Volumes/Zetc-1/Models
- /Volumes/Zetc-1/Studios
- /Volumes/Zetc-1/Uncategorized
- /Volumes/Torrents/Complete/Zetc
- /Volumes/TorrentsOld/Complete/Zetc
- /Volumes/Internal
- /Volumes/External

No fallback directories are allowed for corresponding video discovery.

### 2) Recursive Search

All allowed roots above are searched recursively.

### 3) Marks Directories

- Chapters: /Users/bogwahn/Library/Mobile Documents/com~apple~CloudDocs/Personal/Zetc/Chapters
- Bookmarks: /Users/bogwahn/Library/Mobile Documents/com~apple~CloudDocs/Personal/Zetc/Bookmarks

Lookup order for a video input is always:

1. Chapters
2. Bookmarks

### 4) Conflict Resolution Semantics

If video already has chapters, show a two-column terminal comparison:

1. Text file chapters/bookmarks
2. Existing video chapters

Then prompt for:

1. Keep
2. Replace
3. Merge

Merge rule: deduplicate by timecode only.

## Current Architecture (Implemented)

Implemented componentized CLI in `src/video_file_management/chapterize/cli.py`:

1. `FileKindDetector`: identifies `video`, `bookmarks`, `chapters`, `unknown`
2. `MarksLoader`: reads bookmarks/chapters files into marks model
3. `PathMatchIndex`: indexes Chapters/Bookmarks dirs and resolves best match for video stem
4. `VideoLocator`: searches only configured roots recursively
5. `CLIVideoReaderStrategy`: reads existing video chapters from metadata
6. `CLIVideoWriterStrategy`: writes chapters into target video
7. `MergeService`: merges and deduplicates by timecode
8. `CLIUserPromptStrategy`: renders two-column preview and prompts Keep/Replace/Merge
9. `ChapterizeCommand`: orchestrates end-to-end workflow via DI/composition

## Workflow

### Input handling

1. Accept zero or more paths.
2. If paths are omitted, scan configured video roots recursively.
3. Expand directories recursively into file candidates.

### Per-item processing

1. Detect file kind.
2. If input is a video:
    1. Find matching chapters in Chapters dir.
    2. If missing, find matching bookmarks in Bookmarks dir.
3. If input is bookmarks/chapters:
    1. Resolve corresponding video by searching allowed video roots recursively.
4. Load incoming marks from text file.
5. Read existing embedded video chapters.
6. If existing chapters present:
    1. Show two-column preview.
    2. Prompt Keep/Replace/Merge.
7. Write selected final marks to video.
8. Return structured result entry for summary and exit-code calculation.

## CLI Behavior Contract

### Command

```bash
chapterize [paths ...] [--non-interactive]
```

### Flags

1. `paths ...`:
    1. Optional.
    2. Files and directories.
    3. Directories are recursive.
2. `--non-interactive`:
    1. Skip prompt.
    2. Conflict policy defaults to Replace.

### Exit codes

1. `0`: at least one file processed successfully.
2. `1`: nothing processed or fatal input-level failure.

## Testing Plan

### Already added

`tests/unit/features/chapterize/test_cli_components.py`

1. File-kind detection (bookmarks vs chapters)
2. Chapters preferred over bookmarks for same video stem
3. Merge dedupe by timecode only

### Next tests

1. Unit test: `VideoLocator` enforces strict root allowlist
2. Unit test: no out-of-allowlist fallback for marks-to-video lookup
3. Unit test: two-column prompt formatting for conflicts
4. Integration-style test: orchestration for video input and marks input with mocked writer

## Implementation Status

As of 2026-03-16:

### Done

1. Componentized CLI orchestration in `src/video_file_management/chapterize/cli.py`.
2. Strict video-root allowlist configuration for matching video discovery.
3. Recursive traversal in configured roots and user-provided directories.
4. Chapters-first, Bookmarks-second lookup order for video inputs.
5. Terminal Keep/Replace/Merge conflict resolution flow.
6. Merge dedupe by timecode-only semantics.
7. Initial component tests in `tests/unit/features/chapterize/test_cli_components.py`.

### In Progress

1. Full orchestration tests for mixed input kinds and summary/exit-code behavior.

### Next

1. Add remaining orchestration tests with mocked reader/writer/prompt dependencies.
2. Add explicit allowlist-enforcement tests for `VideoLocator`.
3. Add terminal prompt-format tests to lock conflict-preview output.

## Execution Phases

### Phase A: Lock in invariants

1. Keep strict configured roots immutable in command composition root.
2. Keep recursive traversal for configured roots and directory inputs.
3. Keep lookup order Chapters then Bookmarks.

### Phase B: Complete behavior tests

1. Add missing orchestration tests listed above.
2. Validate result summaries and exit codes under mixed processed/skipped sets.

### Phase C: CLI polish

1. Tighten summary output format for scanability.
2. Add small `--dry-run` option if needed (no write, full resolution and prompt path).

## Risks and Mitigations

1. Module-name ambiguity between `chapterize.py` and `chapterize/` package can confuse static tools.
    1. Mitigation: keep tests importing CLI module via explicit dynamic import where needed.
2. External tools (`ffmpeg`, `MP4Box`) might be unavailable in runtime environments.
    1. Mitigation: maintain clear write failure reporting and test with mocks for core orchestration.

## Definition of Done

1. CLI processes zero-or-more paths and directories recursively.
2. Corresponding video search is restricted to allowed roots only.
3. Video input path resolves Chapters first, then Bookmarks.
4. Conflict prompt supports Keep/Replace/Merge in terminal.
5. Merge dedupes by timecode only.
6. Unit tests cover core components and orchestration edge cases.
