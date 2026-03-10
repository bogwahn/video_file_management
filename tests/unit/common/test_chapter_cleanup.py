from video_file_management.chapter_cleanup import (
    _dedupe_chapters,
    _find_repeated_block,
    _parse_chapter_line,
)


def test_parse_chapter_line_normalizes_time() -> None:
    line = _parse_chapter_line("[0:04:00.000] Scene 1")
    assert line is not None
    assert line.timecode_norm == "00:04:00.000"
    assert line.label == "Scene 1"


def test_dedupe_chapters_removes_repeated_block() -> None:
    lines = [
        _parse_chapter_line("[00:04:00.000] Scene 1"),
        _parse_chapter_line("[00:08:00.000] Scene 2"),
        _parse_chapter_line("[00:10:00.000] Scene 3"),
        _parse_chapter_line("[0:04:00.000] Scene 1"),
        _parse_chapter_line("[0:08:00.000] Scene 2"),
        _parse_chapter_line("[0:10:00.000] Scene 3"),
    ]
    cleaned, repeat_count = _dedupe_chapters([line for line in lines if line])
    assert repeat_count == 2
    assert len(cleaned) == 3
    assert cleaned[0].timecode_norm == "00:04:00.000"


def test_find_repeated_block_handles_multiple_sets() -> None:
    pairs = [("00:00:01.000", "a"), ("00:00:02.000", "b")] * 3
    block_len, repeat_count = _find_repeated_block(pairs)
    assert block_len == 2
    assert repeat_count == 3
