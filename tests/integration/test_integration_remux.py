import os
import shutil
import subprocess
from pathlib import Path
import pytest

TEST_DATA_DIR = Path("/Volumes/Zetc/TestData")

TEST_FILES = [
    TEST_DATA_DIR / "test_1GB.mp4",
    TEST_DATA_DIR / "test_3GB.mp4",
    TEST_DATA_DIR / "test_15GB.mp4",
]

@pytest.fixture(scope="module", autouse=True)
def ensure_test_data() -> None:
    """Ensure the persistent dataset exists."""
    if not TEST_DATA_DIR.exists():
        pytest.skip(f"TestData directory not found at {TEST_DATA_DIR}. Skipping.")
    
    missing = [f.name for f in TEST_FILES if not f.exists()]
    if missing:
        pytest.fail(f"Missing integration test files: {missing}")


@pytest.fixture
def mkv_clone(request, tmp_path_factory) -> Path:
    """Generates an MKV clone from the persistent MP4 for remux testing."""
    mp4_source = request.param
    
    # We want to do the stream clone in the same drive to keep testing realistic but
    # safe from destroying the master files during send2trash.
    workspace = TEST_DATA_DIR / "Workspace"
    workspace.mkdir(exist_ok=True)
    
    mkv_target = workspace / f"{mp4_source.stem}_clone.mkv"
    
    # Clone it natively via FFmpeg stream copy without re-encoding
    if not mkv_target.exists():
        subprocess.run(
            ["ffmpeg", "-i", str(mp4_source), "-c", "copy", "-sn", "-y", str(mkv_target)],
            capture_output=True,
            check=True
        )
        
    yield mkv_target
    
    # Normally send2trash handles this, but a safety cleanup doesn't hurt.
    if mkv_target.exists():
        mkv_target.unlink()

@pytest.mark.parametrize("mkv_clone", TEST_FILES, indirect=True)
def test_remux_zero_copy_cleanup_integration(mkv_clone: Path) -> None:
    """Test that the Remux Quick Action natively consumes an MKV, copies it to MP4, and trashes the MKV."""
    
    expected_mp4 = mkv_clone.with_suffix(".mp4")
    if expected_mp4.exists():
        expected_mp4.unlink()
    
    # 1. Execute the Remux CLI via subprocess
    result = subprocess.run(
        ["python3", "-m", "video_file_management.remux.remux_quickaction", str(mkv_clone)],
        capture_output=True,
        text=True,
        check=False
    )
    
    # 2. Assert Success
    assert result.returncode == 0, f"Remux CLI failed: {result.stderr}"
    
    # 3. Verify MP4 explicitly generated and filled
    assert expected_mp4.exists(), f"Output MP4 was not generated: {expected_mp4}"
    assert expected_mp4.stat().st_size > 1024, "Output MP4 is empty or corrupt."
    
    # 4. Verify Zero-Copy Rule: The original MKV MUST be passed to send2trash and no longer exist in place.
    if "failed to trash original" in result.stdout + result.stderr:
        # NAS systems without a dedicated .Trash directory will reject send2trash. The service correctly 
        # aborts the trash rather than brutally unlinking, so we accept the MKV surviving in this edge case.
        assert mkv_clone.exists(), "Wait, if trash failed, the file should still exist!"
    else:
        assert not mkv_clone.exists(), f"Original MKV file {mkv_clone} was not successfully trashed!"
    
    # Clean up the output artifacts so the workspace is pristine
    expected_mp4.unlink()
    if mkv_clone.exists():
        mkv_clone.unlink()
