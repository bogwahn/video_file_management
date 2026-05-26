# ChapterFileWalker — Development Notes

This file contains high-level definitions for three related projects/tasks:

- ChapterFileWalker (utility)
- ChapterFileService (monitoring service)
- chapterize (CLI/function)

Below are cleaned and corrected descriptions of each item followed by a short
list of open questions and assumptions.

## 1) ChapterFileWalker (utility)

### Purpose

- Search a directory (optionally recursively) for video files that do not
  have the Finder tag `Scenes:Chapters`.

### Behavior

- If a file has tags `Chapters` or `Scenes/Chapters`, remove those tags and
  replace them with the `Scenes:Chapters` Finder tag.
- If the file does not have any corresponding chapters information locally,
  search the iCloud directory `/Personal/Zetc/Chapters` for a matching chapters
  file (exact or fuzzy name match). If no chapters file is found, move on to
  the next file.
- If a chapters file is found, add a text track to the video file that contains
  timestamped chapter entries (timestamp + description) and save the updated
  video file. Then add the `Scenes:Chapters` Finder tag to the video file.

## 2) ChapterFileService (monitoring service)

### Purpose

- Continuously monitor the Zetc share and an iCloud `Bookmarks` directory and
  automatically attach chapters when possible.

### Behavior

- Monitor the Zetc share (recursively) and the iCloud bookmarks directory
  (path: `/Personal/Zetc/Bookmarks` or similar).
- When a new video file appears in the Zetc share, look for a corresponding
  chapters file in `/Personal/Zetc/Chapters`. If not found, look for a
  corresponding bookmarks file in the bookmarks folder. If still not found,
  take no action.
- When a bookmarks file is created or modified, look for a matching video file
  in the Zetc share. If found, convert the bookmarks file into a chapters file
  and add the chapters track to the video.
- Continue monitoring after processing.

## 3) chapterize (function / CLI)

### Purpose

- Provide a simple function or command-line script `chapterize` that accepts
  one or more filenames and attempts to attach chapters from the cloud or
  bookmarks sources.

### Behavior

- For each input filename, look for a corresponding chapters file in
  `/Personal/Zetc/Chapters`. If not found, look in the bookmarks folder.
- If no chapters or bookmarks file is found, exit the operation for that
  filename and return a clear message that no matching chapters/bookmarks were
  found.
- If a chapters file is found, add a text track with the chapters entries and
  save the file. Exit with a summary message listing which chapters were added
  for each processed file.

## Open questions and assumptions

- Exact iCloud paths: I assumed `/Personal/Zetc/Chapters` and
  `/Personal/Zetc/Bookmarks`. Confirm the precise folder names/paths.
- Finder tag behavior: confirm whether replacing existing tags should preserve
  other tags on the file or remove only the old chapter-related tags.
- Chapter file format: what format are the chapter files in (e.g. simple
  timestamped text, JSON, WebVTT, ffmetadata)? Provide an example if possible.
- Video formats: which container formats should be supported (MP4/MKV/MOV)?
- Tooling: prefer `ffmpeg`/`MP4Box`/`AtomicParsley` or a Python library like
  `pymediainfo` and `pymp4`? Confirm preferences.

---

If this looks good I will:

1. Create one execution-plan file per project under `docs/plans/`.
2. Produce a detailed execution plan for the first project (`ChapterFileWalker`) and present it here for review.

Please confirm the open questions above, or tell me to proceed with sensible
defaults (e.g., chapters in a simple timestamped text format and MP4/MOV
containers via `ffmpeg`).
