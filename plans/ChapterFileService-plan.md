# ChapterFileService — Execution Plan

## Overview
ChapterFileService is a long-running service that monitors the Zetc share and
an iCloud bookmarks directory for new or updated video, chapters, or bookmarks
files, and automatically attaches chapters to matching video files.

## Success Criteria
- New or modified bookmarks/chapters files trigger checks for matching video
  files; when found, chapters are embedded and the video tagged.
- Service runs reliably as a background process and recovers gracefully from
  transient errors.

## Scope
Included:
- Watch directories (recursive) and respond to file create/modify events.
- Use `ChapterFileWalker` logic for matching and embedding.
- Ensure idempotency: processing the same change multiple times should not
  corrupt files.

Excluded:
- UI or web dashboards (can be added later).

## Dependencies
- `watchdog` or system-level file event APIs.
- A CLI or library implementation of `ChapterFileWalker` to perform operations.

## Tasks
1. Environment and packaging
   - Decide whether to run as a `systemd`-style service, macOS LaunchAgent, or
     a simple daemon process in a container.
2. Directory watchers
   - Implement robust watchers for both the Zetc share and iCloud bookmarks
     directory (handle network mounts and temporary disconnects).
3. Event handling
   - On relevant events, enqueue jobs (debounce bursts of events). Jobs should
     call into `ChapterFileWalker` functionality with safe guards (timeouts).
4. Job processing
   - Implement worker processes or threads to perform matching and embedding.
5. Logging and metrics
   - Add structured logs and optional monitoring hooks.
6. Recovery
   - Implement retries for transient errors and safe failure states for
     persistent issues.
7. Testing and deployment
   - Integration tests that simulate file events, and a plan for local
     deployment (LaunchAgent, Docker, etc.).

## Estimates
- Watcher & job architecture: 2 days
- Integration with `ChapterFileWalker`: 1-2 days
- Robustness & testing: 2 days
- Total (MVP): 1 week

## Next steps
- Confirm preferred run model on macOS (LaunchAgent vs other).
- Share example bookmarks and chapters formats for conversion.

## Queueing, conversion and interactive prompts

Add the following operational rules to the service design:

- **Priority processing:** MP4 (and MOV) files are prioritized for immediate
  chapter embedding. Non-MP4 files are placed into a conversion queue.
- **Conversion queue semantics:** The conversion queue converts files to MP4
  before chapter embedding. Conversion should try a container remux
  (`ffmpeg -c copy`) first and fall back to re-encoding only when required.
- **Batching & defaults:** Process jobs in batches of `100` by default,
  with the service offering an interactive or policy-driven choice after
  each batch: `continue`, `quit`, or `finish`.
- **Test mode:** The service should honor a `--test-mode` or similar
  configuration to limit processing to at most `10` files for safe testing.

Incorporate these controls into the watcher event handling, the job queue
manager, and service configuration.
