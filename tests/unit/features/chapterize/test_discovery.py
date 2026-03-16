from pathlib import Path

from video_file_management.chapterize.discovery import RecursiveNASDiscovery


def test_recursive_discovery_finds_file_in_subdirectory(tmp_path: Path) -> None:
    # Setup
    root_dir = tmp_path / "Zetc"
    nested_dir = root_dir / "Movies" / "Sci-Fi"
    nested_dir.mkdir(parents=True)

    # Target video deep inside
    target_video = nested_dir / "my_movie.mp4"
    target_video.touch()

    # Noise
    (root_dir / "my_movie.txt").touch()
    (root_dir / "Movies" / "other_movie.mp4").touch()

    discovery = RecursiveNASDiscovery([str(root_dir)])
    result = discovery.find_video("/some/other/path/my_movie.txt")

    assert result == str(target_video.absolute())


def test_recursive_discovery_ignores_recycle_bin(tmp_path: Path) -> None:
    root_dir = tmp_path / "Zetc"
    recycle_bin = root_dir / "#Recycle Bin"
    valid_dir = root_dir / "Movies"

    recycle_bin.mkdir(parents=True)
    valid_dir.mkdir(parents=True)

    # Put the target video in the recycle bin
    recycled_video = recycle_bin / "target_movie.mp4"
    recycled_video.touch()

    discovery = RecursiveNASDiscovery([str(root_dir)])
    result = discovery.find_video("/path/to/target_movie.txt")

    # Should not find the one in the recycle bin
    assert result is None


def test_recursive_discovery_finds_file_in_local_bookmark_dir_first(tmp_path: Path) -> None:
    nas_dir = tmp_path / "Zetc"
    nas_dir.mkdir()

    local_dir = tmp_path / "local_downloads"
    local_dir.mkdir()

    # Define paths
    nas_video = nas_dir / "target_movie.mp4"
    local_video = local_dir / "target_movie.mp4"

    nas_video.touch()
    local_video.touch()

    discovery = RecursiveNASDiscovery([str(nas_dir)])

    # Requesting with a bookmark in the local_dir
    result = discovery.find_video(str(local_dir / "target_movie.txt"))

    # Should prioritize the local one next to the bookmark
    assert result == str(local_video.absolute())


def test_recursive_discovery_returns_none_if_missing(tmp_path: Path) -> None:
    dir1 = tmp_path / "dir1"
    dir1.mkdir()

    discovery = RecursiveNASDiscovery([str(dir1)])
    result = discovery.find_video("/path/to/my_movie.txt")

    assert result is None
