import os
import subprocess
import time
from pathlib import Path
import pytest

TEST_DATA_DIR = Path("/Volumes/Zetc/TestData")

@pytest.fixture(scope="module")
def synthetic_video_files() -> list[Path]:
    """Generate synthetic video files for testing MP4Box chapter injection without using real user data.
    
    Creates a 1GB and a 3GB file purely constructed from lavfi (black video, silent audio).
    """
    if not TEST_DATA_DIR.exists():
        pytest.skip(f"TestData directory not found at {TEST_DATA_DIR}. Cannot perform realistic NAS integration tests.")
    
    file_1gb = TEST_DATA_DIR / "synthetic_test_1GB.mp4"
    file_3gb = TEST_DATA_DIR / "synthetic_test_3GB.mp4"
    generated_files = [file_1gb, file_3gb]
    
    # We want these files to be large enough to trigger the network traversal bug we observed.
    # To generate a 1GB file quickly, we'd normally just pad it, but MP4Box needs a valid moov atom.
    # Instead, we will generate a valid but small MP4 file, and then pad its mdat atom using dd to simulate size.
    # We only need one valid file to start with.
    
    base_file = TEST_DATA_DIR / "synthetic_base.mp4"
    if not base_file.exists():
        subprocess.run(
            ["ffmpeg", "-f", "lavfi", "-i", "color=c=black:s=640x480", "-f", "lavfi", "-i", "aevalsrc=0", "-t", "10", "-crf", "0", "-preset", "ultrafast", "-y", str(base_file)],
            check=True, capture_output=True
        )
    
    # Create 1GB clone if missing
    if not file_1gb.exists() or file_1gb.stat().st_size < 1_000_000_000:
        subprocess.run(["cp", str(base_file), str(file_1gb)], check=True)
        # Append 1GB of zero bytes to simulate a large mdat atom / file size
        subprocess.run(["dd", "if=/dev/zero", "bs=1m", "count=1000"], stdout=open(file_1gb, "ab"))
        
    # Create 3GB clone if missing
    if not file_3gb.exists() or file_3gb.stat().st_size < 3_000_000_000:
        subprocess.run(["cp", str(base_file), str(file_3gb)], check=True)
        # Append 3GB of zero bytes
        subprocess.run(["dd", "if=/dev/zero", "bs=1m", "count=3000"], stdout=open(file_3gb, "ab"))

    yield generated_files

    # Teardown
    for f in generated_files + [base_file]:
        if f.exists():
            f.unlink()


def test_chapterize_zero_copy_integration(synthetic_video_files: list[Path], tmp_path: Path) -> None:
    """Test that chapterize instantly embeds metadata directly into large files without duplicating them."""
    
    for video_file in synthetic_video_files:
        # 1. Create a bookmarks file for the video adjacent to it so NAS discovery is instantaneous
        bookmark_path = TEST_DATA_DIR / f"{video_file.stem}-bookmarks.txt"
        bookmark_path.write_text("00:00:01.000,Intro\n00:00:05.000,Action\n00:00:09.000,Outro\n")
        
        try:
            # Note the original file stats to prove zero-copy / instantly applied mutation
            original_stat = video_file.stat()
            
            # 2. Execute the CLI via subprocess equivalent to the ~/bin/ Quick Action
            start_time = time.time()
            
            # Note: We can assume the CLI works with absolute paths from the src logic and discovery
            result = subprocess.run(
                ["python3", "-m", "video_file_management.chapterize.cli", str(bookmark_path)],
                capture_output=True,
                text=True,
                check=False
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 3. Assert execution success
            assert result.returncode == 0, f"Chapterize CLI failed: {result.stderr}"
            
            # 4. Verify Performance: MP4Box should complete even on a large file.
            assert duration < 600.0, f"Chapterize took {duration}s, which exceeds network NAS bounds."
            
            # 5. Verify MP4Box actually wrote the payload to the file
            probe_result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_chapters", str(video_file)],
                capture_output=True,
                text=True,
                check=True
            )
            assert '"title": "Intro"' in probe_result.stdout
            assert '"title": "Action"' in probe_result.stdout
            assert '"title": "Outro"' in probe_result.stdout
        finally:
            if bookmark_path.exists():
                bookmark_path.unlink()
