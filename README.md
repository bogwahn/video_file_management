# Video File Management Library & Utilities

## Objective

To create a comprehensive library of video file related functions and features that will be used to create CLI commands and other servies and applications.

## Commands

1. `chapterize [file_or_directory]` - finds a matching Chapters file or, if none matches, a Bookmarks file and writes its marks into the video as chapters.
2. remux - by default this command will remux from any compatible container to the mp4 file type.  Other remuxes will also be made available
3. transcode - does the full transcoding of a video file from one type to another.  The default and focus is to create the smallest files possible by using the AV1 format.

### Chapterize

The `chapterize` command requires the `icloud` environment variable to point to the iCloud root. It searches for mark files in `$icloud/Personal/Zetc/Chapters` and `$icloud/Personal/Zetc/Bookmarks`. With no argument, it processes video candidates in the current directory; with a directory argument, it scans only that directory, not its subdirectories. A single video file can also be passed directly.

Video candidates use the `.mp4`, `.mkv`, `.mov`, `.m4v`, `.avi`, `.wmv`, `.webm`, `.mpg`, `.mpeg`, `.ts`, and `.m2ts` extensions, case-insensitively. The video and mark-file names are matched after removing resolution labels (`480p`, `540p`, `720p`, `1080p`, `2k`, `4k`, `5k`, `6k`, `7k`, or `8k`); bookmark names additionally remove the `-bookmarks` suffix. A unique match is used directly; among multiple matches, the first alphabetically with at least three marks is selected. When both source types match, the Chapters file is preferred and the lists are not merged. If only a Bookmarks file matches, its entries are written as chapters; if neither matches, the command reports that no matching file was found.

MP4 videos are written with MP4Box; other supported containers use an FFmpeg stream-copy remux with native chapter metadata. The original video is replaced only after the output has been produced successfully.

### The Tools

We will develop a set of tools that starts with the vfw prefix.  for instance there will be a feature that show you the compreshensive metadata for a file in a readable fashion.  vfw showMetadata <file_name>

## Software Architecture

### Models

#### Required

1. Videomark (videomark.py) - a Python Protocol that represents a video bookmark, storing information about chapters and bookmarks within a video file.
2. Bookmark (bookmark.py) - an implelmentation of the Videomark protocol, representing a specific bookmark within a video file.
3. Chapter (chapter.py) - an implementation of the Videomark protocol, representing a specific chapter within a video file.
4. Timecode (timecode.py) - a class representing a timecode within a video file, used for precise timing and synchronization of chapters and bookmarks.
5. VideoMarksFile (videomarks_file.py) - a Protocol representing a file containing video marks, used to manage and organize chapters and
bookmarks within a video file.
6. VideoMarksFileABC (videomarks_file_abc.py) - an abstract base class providing a common interface and shared functionality for managing video marks files.
7. BookmarksFile (bookmarks_file.py) - a concrete implementation of the VideoMarksFile protocol, specifically for managing bookmark files within a video file. Will have an additional property called Bookmarks which is a list of Bookmark instances.
8. ChaptersFile (chapters_file.py) - a concrete implementation of the VideoMarksFile protocol, specifically for managing chapter files within a video file.  Will have an additional property called Chapters which is a list of Chapter instances.
9. VideoMarksFileReader (videomarks_filereader.py) - a Protocol defining a method called read() that reads a file and returns a VideoMarksFile. Implementations take the filename in their constructor and do not touch the file until read() is called.
10. VideoMarksFileWriter (videomarks_filewriter.py) - a Protocol defining a method called write(file) that writes the given VideoMarksFile to a file. Implementations take the filename in their constructor and do not touch the file until write() is called.
11. VideoMarkABC (videomark_abc.py) - an abstract base class for marks, holding time and label and requiring to_string().
12. BookmarksFileReader (bookmarks_filereader.py) - implements VideoMarksFileReader; read() parses "HH:MM:SS.mmm,Label" lines and returns a BookmarksFile. Blank lines are ignored and malformed lines raise a ValueError naming the line.
13. ChaptersFileReader (chapters_filereader.py) - implements VideoMarksFileReader; read() parses "[HH:MM:SS.mmm] Label" lines and returns a ChaptersFile. Blank lines are ignored and malformed lines raise a ValueError naming the line.
14. BookmarksFileWriter (bookmarks_filewriter.py) - implements VideoMarksFileWriter; write(file) serializes the marks as bookmark lines.
15. ChaptersFileWriter (chapters_filewriter.py) - implements VideoMarksFileWriter; write(file) serializes the marks as chapter lines.
Readers and writers are created by dependency injection (to be implemented later), which supplies the filename.
16. Resolution (resolution.py) - an immutable value object holding the width and height of a video in pixels.
17. VideoFile (video_file.py) - an immutable, read-only description of a video file that performs no file I/O. Path-derived properties: Filename (name with extension), Ext (extension including the dot) and FullPath (absolute path). Metadata properties, supplied by the caller and None when unknown: Resolution, FinderTags (tuple of strings), Container, Duration (a TimeCode), VideoCodec, AudioCodec, FrameRate (frames per second), Bitrate (bits per second) and FileSize (bytes) and Chapters (a list of Chapter instances, empty when the file has none; each access returns a copy).

## Next Steps

1. Review and integrate the chapterize implementation, including its file discovery, mark selection, and container-specific chapter writers.
2. Define the intended video metadata and Finder tag behavior before implementing those functionality-list items.

Refer to the [Chapterize Functionality List](docs/chapterize/functionality_list.md) for a detailed overview of the features and capabilities of the chapterize functionality.
