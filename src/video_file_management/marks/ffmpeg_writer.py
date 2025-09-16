from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .protocols import VideoMarksFile
from ..utils.timecode import parse_timecode


def generate_ffmetadata(chapters: VideoMarksFile, video_duration_ms: int) -> str:
    """Generate ffmpeg ffmetadata format from chapters.
    
    Returns text content ready to write to a .ffmetadata file.
    Each chapter starts exactly at its timestamp and ends when the next begins.
    No chapter at 0:00:00 - first chapter starts at first mark timestamp.
    """
    marks = list(chapters.marks())
    if not marks:
        return ";FFMETADATA1\n"
    
    lines = [";FFMETADATA1"]
    
    for i, mark in enumerate(marks):
        start_ms = int(
            parse_timecode(f"{mark.timecode}").total_seconds() * 1000
        )
        
        # End time is start of next chapter, or video end for last chapter
        if i + 1 < len(marks):
            end_ms = int(
                parse_timecode(f"{marks[i+1].timecode}").total_seconds() * 1000
            )
        else:
            end_ms = video_duration_ms
        
        lines.extend([
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={start_ms}",
            f"END={end_ms}",
            f"title={mark.label}",
        ])
    
    return "\n".join(lines) + "\n"


class FFmpegChapterWriter:
    """Embeds chapters into MP4 using ffmpeg and ffmetadata format."""
    
    def write(self, video_file_path: str, chapters: VideoMarksFile) -> None:
        """Write chapters to video file using ffmpeg."""
        video_path = Path(video_file_path)
        if not video_path.exists() or not video_path.is_file():
            return
        
        # Get video duration
        try:
            duration_ms = self._get_video_duration_ms(str(video_path))
        except Exception:
            return
        
        # Generate ffmetadata
        ffmetadata_content = generate_ffmetadata(chapters, duration_ms)
        
        # Write chapters using ffmpeg
        try:
            self._embed_chapters_ffmpeg(str(video_path), ffmetadata_content)
        except Exception:
            return
    
    def _get_video_duration_ms(self, video_path: str) -> int:
        """Get video duration in milliseconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        duration_seconds = float(data["format"]["duration"])
        return int(duration_seconds * 1000)
    
    def _embed_chapters_ffmpeg(
        self, video_path: str, ffmetadata_content: str
    ) -> None:
        """Embed chapters using ffmpeg and ffmetadata."""
        video = Path(video_path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            ffmetadata_file = temp_path / "chapters.ffmetadata"
            temp_video_clean = temp_path / "temp_no_chapters.mp4"
            temp_video = temp_path / "temp_with_chapters.mp4"
            
            # Write ffmetadata file
            ffmetadata_file.write_text(ffmetadata_content, encoding="utf-8")
            
            # Step 1: Strip all existing chapters
            cmd1 = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", str(video),
                "-map", "0",
                "-map_chapters", "-1",
                "-c", "copy",
                "-y", str(temp_video_clean)
            ]
            subprocess.run(cmd1, check=True)
            
            # Step 2: Add only our specific chapters
            cmd2 = [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", str(temp_video_clean),
                "-i", str(ffmetadata_file),
                "-map", "0",
                "-map_chapters", "1",
                "-c", "copy",
                "-y", str(temp_video)
            ]
            subprocess.run(cmd2, check=True)
            
            # Verify the output file exists and is valid
            if not temp_video.exists() or temp_video.stat().st_size == 0:
                raise RuntimeError("FFmpeg output file is missing or empty")
            
            # Safe atomic replacement: create backup, replace, cleanup
            backup_path = video.with_suffix(video.suffix + ".bak")
            try:
                # Remove any existing backup
                if backup_path.exists():
                    backup_path.unlink()
                # Move original to backup
                video.rename(backup_path)
                # Move new file to original location
                temp_video.rename(video)
                # Remove backup on success
                backup_path.unlink()
            except Exception:
                # If anything fails, try to restore from backup
                if backup_path.exists() and not video.exists():
                    backup_path.rename(video)
                raise 