# Chapterize Video Project Statement

## 1. Goals
The overarching goal of the Chapterize Video project is to enhance the `video_file_management` toolkit by providing a seamless, context-menu-driven workflow for macOS users to permanently embed chapters into video files directly from a bookmarks file. This feature aims to streamline the post-processing workflow by leveraging existing tools like `ffmpeg` transparently and providing intuitive user conflict resolution when existing chapters are detected.

Crucially, this new addition will strictly adhere to the project's Object-Oriented nature. A Controller (or Composite) object will be created to orchestrate the workflow, while remaining entirely independent from the actual execution of the tasks. The actual work will be delegated to cohesive, reusable components that can be aggregated for future use cases.

## 2. Objectives
1. **Context Menu Integration**: Create a macOS Quick Action that allows a user to right-click on a bookmarks file and select "Chapterize Video".
2. **Abstract Documented Architecture**: Strictly adhere to SOLID design principles, GoF design patterns, "program to an interface, not an implementation", and "favor composition over inheritance."
3. **Smart Video Discovery**: Create a component to locate the target video file. Since the bookmarks file will almost never execute from the same directory as the video file, the system must search a predefined list of directories to locate the corresponding video file reliably.
4. **Chapter Detection & Preview**: Utilize a component to inspect the target video file for pre-existing chapters. Formulate a rich text payload illustrating the existing chapters, the new bookmark-derived chapters, and a preview of what a "Merge" would look like.
5. **Interactive User Resolution**: Display a macOS native UI dialog (using the generated chapter previews) asking the user to choose between:
   - **Keep**: Retain the current chapters and abort the injection of new bookmarks.
   - **Replace**: Overwrite the existing chapters entirely with the newly converted bookmarks.
   - **Merge**: Combine the existing chapters with the new bookmarks (converted to chapters).
6. **Graceful Failures & Error Reporting**: Enforce strict error handling. If an abort is necessary, the user must always be presented with a clear GUI notification detailing exactly what went wrong (e.g., "Video file not found", "ffmpeg missing").
7. **Safe Embedding for Large Files**: Leverage `ffmpeg` (or `MP4Box`) to embed the finalized chapters. Given that video files may exceed 15GB, a full pre-process backup is undesirable. The script must implement localized, space-efficient safety mechanisms (e.g., executing an atomic replacement via temporary files) to prevent data corruption.

## 3. Requirements

### 3.1 Functional Requirements
- **Triggering**: The action must be initiable from macOS Finder via a right-click Context Menu (Quick Action / Service) on text-based bookmark files.
- **Video Discovery Component**: Must accept the bookmarks file name/stem and scan a configurable set of directories (defined by the system) to find the matching video file.
- **Progress Notifications**: The user must receive non-blocking, transient UI notifications (e.g., macOS Notifications) detailing the current background processes, such as "Locating associated video file...", "Checking for existing chapters...", and "Embedding new chapters...".
- **Controller Object Orchestration**: A central `ChapterizeController` must orchestrate the flow. It delegates discovery, probing, prompt generation, merging, and writing to individual, specialized components implementing defined protocols.
- **Rich Interactive Prompt**: A rich UI dialog must be presented to the user showing the *Currently Embedded Chapters*, the *New Chapters (from Bookmarks)*, and a *Merged Preview*, accompanied by the "Keep", "Replace", and "Merge" action buttons.
- **Embedding Component**: The component responsible for writing must apply the new chapter metadata to the target video using `ffmpeg` without re-encoding the video or audio streams.

### 3.2 Non-Functional Requirements
- **Design Constraints**: The system must utilize composition to build the Controller. Dependencies must be injected via interfaces (Protocols in Python) rather than concrete implementations.
- **Safety**: The embedding process must write the output to a temporary file on the same volume as the source. Only upon successful completion will the temporary file atomically replace the original file, avoiding the storage overhead of full duplication.
- **Extensibility**: The Python script executing the logic must be modular, allowing the controller to be attached to other UI paradigms beyond macOS Quick Actions (e.g., CLI, web interface) seamlessly.
- **One-Click Deployment**: The system must provide a truly native, literal "one-click" deployment solution that installs the backend packages, sets up wrapper scripts, and creates the macOS Quick Actions inside `/Library/Services/` without requiring any Terminal or Automator interaction from the end-user.
