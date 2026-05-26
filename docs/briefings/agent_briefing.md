# Agent Briefing: video-file-management Refactor

## Project

Python CLI tool (`src/video_file_management/`). Two working commands installed globally via pipx: `chapterize` and `remux`. Python ≥3.10, src-layout, pytest, black, isort, mypy.

## What's Done

- Phase 1: Deleted 27 dead files, renamed `remux2mp4` → `remux` throughout
- Phase 2: pipx install live; `chapterize` and `remux` verified working globally
- Phase 3 (docs only): Architecture design written to `docs/design/architecture.md`

**Do not break the working commands. All migrations must keep tests green.**

## Target Folder Structure

```
src/video_file_management/
├── commands/
│   ├── chapterize/        # cli.py + orchestrator.py + discovery.py + merger.py + resolver.py
│   └── remux/
│       ├── cli.py
│       ├── orchestrator.py
│       ├── quickaction.py
│       └── mp4/           # config.py + policy.py + service.py
├── domain/
│   ├── videomarks/        # videomark.py + chapter.py + bookmark.py + videomarks_file.py + chapters_file.py + bookmarks_file.py
│   ├── video/             # video_file.py + stream_info.py + compatibility.py
│   ├── readers/           # chapters_file_reader.py + bookmarks_file_reader.py + videofile_reader.py + videofile_metadata_reader.py
│   ├── writers/           # chapter_write_strategy.py + mp4_chapters_writer.py + xattr_chapters_writer.py
│   ├── tagging/           # tag_backend.py + finder.py
│   ├── storage/           # storage_backend.py + local.py + smb.py + afp.py
│   └── shared/            # timecode.py + command_runner.py + file_collector.py + result.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── load/
├── scripts/
├── deploy/
└── docs/
```

## Current File → New Location Map

| Current file | New location | Action |
|---|---|---|
| `marks/models.py` | `domain/videomarks/videomark.py` | Move + convert `VideoMark` to Protocol |
| `marks/protocols.py` | `domain/videomarks/videomarks_file.py` | Move, rename class to match file |
| `marks/chapters_file.py` | `domain/videomarks/chapters_file.py` | Move + fix `List`→`list` |
| `marks/readers.py` | `domain/readers/chapters_file_reader.py` | Move, `file_path: str`→`Path` |
| `marks/bookmarks_reader.py` | `domain/readers/bookmarks_file_reader.py` | Move + fix return type (returns `ChaptersFile`, should return `BookmarksFile`) |
| `marks/writers.py` | `domain/writers/mp4_chapters_writer.py` + `xattr_chapters_writer.py` | Split into two files |
| `chapter_reader.py` | `domain/readers/videofile_reader.py` | Move + rename class + fix `List`→`list` |
| `metadata_reader.py` | `domain/readers/videofile_metadata_reader.py` | Move + rename class + fix `List`→`list` |
| `tag_reader.py` | `domain/tagging/finder.py` | Move + rename to `FinderTagBackend` class + fix `List`→`list` |
| `utils/timecode.py` | `domain/shared/timecode.py` | Move |
| `remux/service.py` | Split across `commands/remux/mp4/` + `domain/shared/` | See decomposition below |
| `remux/cli.py` | `commands/remux/cli.py` | Move + update imports |
| `remux/remux_quickaction.py` | `commands/remux/quickaction.py` | Move (rename file only) |
| `chapterize/cli.py` | `commands/chapterize/` | Split into cli + orchestrator + discovery + merger + resolver |
| `domain/__init__.py` | (already exists, keep) | No change |

## Objects to Create (Don't Exist Yet)

| File | Object | What it is |
|---|---|---|
| `domain/videomarks/chapter.py` | `Chapter` | `@dataclass(frozen=True, slots=True)` with `title: str`, `timecode: timedelta`. Implements `VideoMark` protocol. |
| `domain/videomarks/bookmark.py` | `Bookmark` | Same shape as `Chapter`. Distinct type for semantic clarity. |
| `domain/videomarks/bookmarks_file.py` | `BookmarksFile` | Mirror of `ChaptersFile` but holds `Bookmark` objects, serializes as `HH:MM:SS.mmm,Title`. |
| `domain/shared/result.py` | `Result[T]` | `@dataclass` with `data: T \| None`, `errors: list[str]`, `partial: bool`, `ok() -> bool` method. |
| `domain/shared/command_runner.py` | `CommandRunner`, `CommandResult` | Extracted from `remux/service.py`. Shared subprocess wrapper. |
| `domain/shared/file_collector.py` | `FileCollector` | Extracted from `remux/service.py` (`InputCollector`). Generalized to accept any extension set. |
| `domain/storage/storage_backend.py` | `StorageBackend` | Protocol: `exists`, `read_bytes`, `write_bytes`, `list_files`, `move`, `delete`. |
| `domain/storage/local.py` | `LocalBackend` | Concrete `StorageBackend` over local filesystem. |
| `domain/storage/smb.py` | `SMBBackend` | Stub only — protocol impl, raise `NotImplementedError`. |
| `domain/storage/afp.py` | `AFPBackend` | Stub only — protocol impl, raise `NotImplementedError`. |
| `domain/tagging/tag_backend.py` | `TagBackend` | Protocol: `read_tags`, `write_tags`, `add_tag`, `remove_tag`. |
| `domain/writers/chapter_write_strategy.py` | `ChapterWriteStrategy` | Protocol: `write(video_path, chapters) -> Result[None]`. |
| `commands/remux/mp4/config.py` | `MP4Config` | Rename of `Remux2Mp4Config`. Same fields. |
| `commands/remux/mp4/policy.py` | `MP4CompatibilityPolicy` | Extracted from `remux/service.py`. |
| `commands/remux/mp4/service.py` | `MP4Service` | Extracted from `Remux2Mp4Service`. Implements `FormatService` protocol. |
| `commands/remux/orchestrator.py` | `RemuxOrchestrator` | Thin coordinator: injects `FileCollector` + `MP4Service`. |
| `commands/chapterize/orchestrator.py` | `ChapterizeOrchestrator` | Extracted from monolithic `chapterize/cli.py`. |
| `commands/chapterize/discovery.py` | `VideoDiscovery` | Extracted `PathMatchIndex` + `VideoLocator` logic from `chapterize/cli.py`. |
| `commands/chapterize/merger.py` | `ChapterMerger` | Extracted merge logic from `chapterize/cli.py`. |
| `commands/chapterize/resolver.py` | `ConflictResolver` | Extracted conflict resolution from `chapterize/cli.py`. |

## Key Decomposition: `remux/service.py`

Current file contains 6 distinct things. Split as follows:

| Current class | New home |
|---|---|
| `Remux2Mp4Config` | `commands/remux/mp4/config.py` → rename `MP4Config` |
| `RunResult` + `CommandRunner` | `domain/shared/command_runner.py` → rename `CommandResult` + `CommandRunner` |
| `StreamInfo` | `domain/video/stream_info.py` |
| `CompatibilityReport` + `Mp4CompatibilityPolicy` | `commands/remux/mp4/policy.py` |
| `InputCollector` | `domain/shared/file_collector.py` → rename `FileCollector`, generalize extensions param |
| `Remux2Mp4Service` | `commands/remux/mp4/service.py` → rename `MP4Service` |
| `RemuxStatus` (enum) | `commands/remux/mp4/service.py` → rename `RemuxStatus` |

## Key Decomposition: `chapterize/cli.py`

All business logic is crammed into this one file (~700 lines). Extract as follows:

| Logic currently in `cli.py` | New home |
|---|---|
| `PathMatchIndex` + `VideoLocator` (fuzzy name matching) | `commands/chapterize/discovery.py` → `VideoDiscovery` |
| Chapter merge logic (diff, overlap detection) | `commands/chapterize/merger.py` → `ChapterMerger` |
| Keep/Replace/Merge prompt + force flag | `commands/chapterize/resolver.py` → `ConflictResolver` |
| `_prepare_video_for_chapterize()` (MKV→MP4) | `commands/chapterize/orchestrator.py` (delegates to injected `MP4Service`) |
| Config constants (`CONFIGURED_VIDEO_ROOTS`, dirs) | `commands/chapterize/config.py` → `ChapterizeConfig` dataclass |
| Main run loop | `commands/chapterize/orchestrator.py` → `ChapterizeOrchestrator.run()` |
| argparse | `commands/chapterize/cli.py` (stays, just thinner) |

## Critical Constraints

1. **`chapterize` and `remux` must keep working** throughout migration. Migrate in steps; update imports after each move.
2. **Rename `label` → `title`** on `VideoMark`/`Chapter`/`Bookmark`. Current code uses `label`; architecture uses `title`. Update all call sites.
3. **`BookmarksFileReader` has a bug**: currently returns `ChaptersFile`. Fix to return `BookmarksFile` when `BookmarksFile` is created.
4. **`List` → `list`** in all type hints (Python 3.9+). Affects: `ChaptersFile`, `ChapterReadResult`, `TagReadResult`, `BookmarksFileReader`.
5. **`file_path: str` → `file_path: Path`** in `VideoMarksFile` protocol and implementations. Update all callers.
6. **`Remux2Mp4*` naming is gone.** All classes rename per the map above. Update all import sites (chapterize/cli.py imports `Remux2Mp4Config`, `Remux2Mp4Service`, `RemuxStatus`).
7. **pyproject.toml entry points** must stay pointed at working `main()` functions throughout.
8. **Tests live in `tests/unit/` and `tests/integration/`**. Update imports in test files after each move.
9. **Delete `marks/` and `utils/` packages** only after all content has been moved and imports updated.

## Migration Order (safe sequence)

1. Create `domain/shared/result.py` (no dependencies)
2. Create `domain/shared/timecode.py` (move from `utils/timecode.py`)
3. Create `domain/shared/command_runner.py` (extract from `remux/service.py`)
4. Create `domain/shared/file_collector.py` (extract from `remux/service.py`)
5. Create `domain/videomarks/` (move + create Chapter, Bookmark, BookmarksFile)
6. Create `domain/readers/` (move all readers; fix BookmarksFileReader return type)
7. Create `domain/writers/` (split `marks/writers.py`)
8. Create `domain/tagging/` (move `tag_reader.py`)
9. Create `domain/storage/` (new: StorageBackend + LocalBackend + stubs)
10. Create `commands/remux/mp4/` (extract from `remux/service.py`; update imports)
11. Create `commands/remux/orchestrator.py` (thin wrapper)
12. Update `remux/cli.py` → `commands/remux/cli.py` imports
13. Create `commands/chapterize/` services (discovery, merger, resolver, orchestrator)
14. Slim down `chapterize/cli.py` → `commands/chapterize/cli.py`
15. Delete old packages (`marks/`, `utils/`, root-level `chapter_reader.py`, `metadata_reader.py`, `tag_reader.py`)
16. Run full test suite; fix any broken imports
