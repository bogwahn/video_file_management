from pathlib import Path

from video_file_management.bookmarks import convert_bookmarks_to_mchapters

BOOKMARKS_SAMPLE = """0:10:05.647,Strip
0:10:41.758,Reveal
0:20:14.597,Missionary
0:26:21.897,Prone Bone
0:32:20.355,RCG
0:40:07.205,OMF - NIce!
"""

EXPECTED_TITLE = "Alex.Grey.BANG!RealTeens.Exclusive.Amateur.Teen.Alex.Grey.Models.For.BANG!1080p"

EXPECTED_CHAPTER_TEXT = "\n".join(
    [
        EXPECTED_TITLE,
        "Language: English",
        "",
        "<@TimeScale:1000>",
        "<@Start>",
        "[00:10:05.647] Strip",
        "[00:10:41.758] Reveal",
        "[00:20:14.597] Missionary",
        "[00:26:21.897] Prone Bone",
        "[00:32:20.355] RCG",
        "[00:40:07.205] OMF - NIce!",
        "<@End>",
    ]
)


def test_convert_bookmarks_to_mchapters(tmp_path: Path) -> None:
    bookmarks_path = tmp_path / (
        "Alex.Grey.BANG!RealTeens.Exclusive.Amateur.Teen.Alex.Grey.Models.For.Bang!1080p-bookmarks.txt"
    )
    bookmarks_path.write_text(BOOKMARKS_SAMPLE, encoding="utf-8")

    output_path = tmp_path / f"{EXPECTED_TITLE}.txt"
    result_path = convert_bookmarks_to_mchapters(
        bookmarks_path,
        output_path=output_path,
        title=EXPECTED_TITLE,
    )

    assert result_path == output_path
    assert output_path.read_text(encoding="utf-8") == EXPECTED_CHAPTER_TEXT
