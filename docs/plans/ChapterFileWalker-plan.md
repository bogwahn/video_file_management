# ChapterFileWalker — Execution Plan

## Overview

ChapterFileWalker is a utility that scans a directory (optionally
recursively) to find video files without a `Scenes:Chapters` Finder tag, finds
or generates matching chapters data, adds a chapters text track to the video,
and tags the file.

## Success Criteria

- Video files that have valid chapters receive an embedded text chapter track
  and are tagged with `Scenes:Chapters`.
- Files without available chapters are left unchanged and logged.
- The utility can run as a one-shot CLI or as part of a larger workflow.

## Scope

Included:

- Local directory scans (recursive optionally).
- Finder tag detection and replacement (only chapter-related tags).
- Matching to chapters files in `/Personal/Zetc/Chapters` (exact or fuzzy).
- Adding chapters text track to MP4/MOV (initial support) via `ffmpeg` or
  `MP4Box`.

Excluded:

- Full service monitoring (covered by `ChapterFileService`).
- Automated bookmarks -> chapters conversion (except where a chapters file
  already exists or conversion is trivial and well-defined).

## Assumptions

- Chapters files are in a simple timestamped text format (e.g. `00:00:00 Title`).
- Primary containers are MP4 and MOV. MKV support can be added later.
- macOS Finder tagging is used for workflow state.

## Dependencies

- `ffmpeg` and/or `MP4Box` for embedding text tracks.
- Python 3.10+ (suggested) and libraries: `watchdog` (if watching),
  `python-magic` (optional), and an MP4 helper if needed.

## Tasks (implementation)

1. Project scaffolding

- Create repository layout: `src/`, `tests/`, `docs/plans/`, `scripts/`.
- Add `pyproject.toml` or `requirements.txt`.

2. File discovery
   - Implement recursive directory traversal with filters for video file
     extensions (configurable).
   - Read Finder tags (use `xattr` / macOS APIs or `mdls` to inspect tags).
2. Tag normalization
   - Detect `Chapters` and `Scenes/Chapters` tags, remove only those, and add
     `Scenes:Chapters` while preserving unrelated tags.
3. Chapters lookup
   - Implement name-matching heuristics (exact match, ignoring extension,
     fuzzy match by levenshtein or simple substring matching).
   - Search `/Personal/Zetc/Chapters` for candidate files.
4. Chapters parsing
   - Implement parser for the chosen chapter file format. Provide a JSON
     intermediate representation: [{start: '00:00:00', title: '...'}, ...]
5. Embedding chapters
   - Implement embedding via `ffmpeg` or `MP4Box`. Create helper wrappers that
     accept the video path and chapter list and produce an updated file.
   - Prefer in-place atomic save: write to temporary file and move/replace.
6. CLI
   - Add `chapterfilewalker` CLI with options: `--path`, `--recursive`,
     `--dry-run`, `--tag-only`, `--format`.
7. Tests & validation
   - Unit tests for matching, parsing, and tag operations.
   - Integration test that runs on a small sample MP4 and a chapters file.
8. Documentation
   - Usage examples, known limitations, and developer notes.

## Example embedding approach (notes)

- ffmpeg can add chapters using an `ffmetadata` file and `-i`/`-map_metadata`.
- Example flow:
  1. Convert chapter list to `ffmetadata` format.
  2. Run `ffmpeg -i in.mp4 -i metadata.txt -map_metadata 1 -codec copy out.mp4`.
- Alternative: `MP4Box` or other toolkit depending on reliability.

## Acceptance tests

- Given a sample MP4 and a valid chapters file, running the CLI with
  `--dry-run` should report planned changes.
- Running without `--dry-run` should produce `out.mp4` with embedded chapters
  and set Finder tag `Scenes:Chapters`.

## Estimates

- Spike / research (ffmpeg/MP4Box): 1 day
- Core implementation (discovery, matching, tagging): 2-3 days
- Chapters parsing + embedding: 2 days
- Tests + docs: 1-2 days
- Total (MVP): ~1 week

## Risks and mitigations

- Finder tag manipulation may require macOS-specific APIs; mitigate by
  using `xattr` or `mdls` and testing on target macOS versions.
- Chapter format ambiguity: require/define a canonical input format and
  provide converters.

## Next steps

1. Confirm chapter file format and iCloud paths.
2. Decide embedding tool (`ffmpeg` recommended default).
3. I will produce an initial PR scaffold and the first working spike embedding
   a sample chapter track.

## Queueing, conversion and test-mode (new requirements)

These rules incorporate the user's requirements about prioritization and
conversion behavior:

- **MP4 Priority:** If a candidate video file is already an MP4 (or MOV),
  attempt chapter embedding immediately (higher priority queue).
- **Conversion Queue:** Non-MP4 files are placed into a conversion queue. The
  conversion queue items are lower priority and are converted to MP4 before
  embedding. Conversion should avoid re-encoding when possible (use
  `ffmpeg -c copy` first), falling back to re-encoding only when necessary.
- **Default Queue Size:** Jobs are processed in batches/queues with a
  default size of `100` items.
- **Interactive Prompts:** After each queue/batch finishes, present an
  interactive prompt with options: `continue` (process the next queue),
  `quit` (exit gracefully), or `finish` (process the rest of the queues
  without further prompts). Services or `--non-interactive` runs should
  default to `finish` behavior.
- **Test Mode:** Provide a `--test-mode` that limits the total number of
  processed files to at most `10` for safe testing until integration tests
  pass.
- **Finder Tag Semantics:** Preserve unrelated Finder tags when adding
  `Scenes:Chapters`; only remove/replace chapter-related tags (e.g.
  `Chapters`, `Scenes/Chapters`).

These semantics should be added to the implementation and the tests. Add
small integration tests that exercise the priority queue and `--test-mode`.
