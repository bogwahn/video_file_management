from pathlib import Path

from video_file_management.file_walker import iter_video_files


def test_iter_video_files_respects_recursion_and_extensions(tmp_path: Path) -> None:
    root = tmp_path
    (root / "a.mp4").write_text("")
    (root / "ignore.txt").write_text("")
    sub = root / "nested"
    sub.mkdir()
    (sub / "b.mov").write_text("")
    (sub / "c.mkv").write_text("")

    default_recursive = sorted(p.relative_to(root).as_posix() for p in iter_video_files(root))
    assert default_recursive == ["a.mp4", "nested/b.mov", "nested/c.mkv"]

    shallow = [p.name for p in iter_video_files(root, recursive=False)]
    assert shallow == ["a.mp4"]

    mkv_only = [p.name for p in iter_video_files(root, extensions=["mkv"])]
    assert mkv_only == ["c.mkv"]
