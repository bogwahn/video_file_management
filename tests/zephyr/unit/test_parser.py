"""Unit tests for Zephyr filename grammar parser."""

import pytest

from video_file_management.zephyr.parser import (
    ParseError,
    build_filename,
    normalize_studio,
    parse_filename,
    resolution_from_dimensions,
    try_parse_filename,
)


def test_normalize_studio_compact_no_dots():
    assert normalize_studio("New Sensations") == "NewSensations"
    assert normalize_studio("New.Sensations") == "NewSensations"
    assert normalize_studio("Blacked Raw") == "BlackedRaw"


def test_parse_non_vr_multi_actor():
    name = "Jane.Doe.And.John.Smith.Bang.Scene.Title.4k.mp4"
    p = parse_filename(name)
    assert p.actors == ("Jane.Doe", "John.Smith")
    assert p.studio == "Bang"
    assert p.title == "Scene.Title"
    assert p.resolution == "4k"
    assert p.is_vr is False
    assert p.extension == "mp4"
    assert p.first_actress == "Jane.Doe"


def test_parse_vr_single_actor():
    name = "Jane.Doe.VirtualReal.Scene.Title.4k.VR.mp4"
    p = parse_filename(name)
    assert p.actors == ("Jane.Doe",)
    assert p.studio == "VirtualReal"
    assert p.title == "Scene.Title"
    assert p.is_vr is True
    assert p.resolution == "4k"


def test_parse_vr_three_actors():
    name = "Jane.Doe.And.John.Smith.And.Alex.Lee.Studio.Name.Title.4k.VR.mp4"
    p = parse_filename(name)
    assert p.actors == ("Jane.Doe", "John.Smith", "Alex.Lee")
    assert p.studio == "Studio"
    assert p.title == "Name.Title"
    assert p.is_vr is True


def test_parse_newsensations_with_resolution():
    name = (
        "Paris.White.NewSensations.Babysitter.Paris.White."
        "Is.On.The.Naughty.Slut.List.4k.mp4"
    )
    p = parse_filename(name)
    assert p.studio == "NewSensations"
    assert p.resolution == "4k"
    assert p.actors == ("Paris.White",)


def test_parse_newsensations_without_resolution():
    name = (
        "Paris.White.NewSensations.Babysitter.Paris.White."
        "Is.On.The.Naughty.Slut.List.mp4"
    )
    p = parse_filename(name)
    assert p.studio == "NewSensations"
    assert p.resolution is None
    assert p.title == "Babysitter.Paris.White.Is.On.The.Naughty.Slut.List"
    assert p.is_vr is False


def test_build_roundtrip_dotted_resolution():
    name = build_filename(
        actors=["Jane Doe", "John Smith"],
        studio="Bang",
        title="Scene Title",
        resolution="4k",
        extension="mp4",
        is_vr=False,
    )
    assert name == "Jane.Doe.And.John.Smith.Bang.Scene.Title.4k.mp4"
    assert ".4k." in name
    assert "Title4k" not in name
    assert parse_filename(name).actors == ("Jane.Doe", "John.Smith")


def test_build_omits_unknown_resolution():
    name = build_filename(
        actors=["Paris White"],
        studio="New Sensations",
        title="Babysitter Paris White Is On The Naughty Slut List",
        resolution=None,
        extension="mp4",
    )
    assert name == (
        "Paris.White.NewSensations.Babysitter.Paris.White."
        "Is.On.The.Naughty.Slut.List.mp4"
    )
    assert ".4k." not in name
    assert ".NewSensations." in name
    p = parse_filename(name)
    assert p.resolution is None
    assert p.studio == "NewSensations"


def test_build_newsensations_with_resolution():
    name = build_filename(
        actors=["Paris White"],
        studio="New Sensations",
        title="Scene Title",
        resolution="1080p",
    )
    assert name == "Paris.White.NewSensations.Scene.Title.1080p.mp4"


def test_build_vr_marker_before_ext():
    name = build_filename(
        actors=["Jane.Doe"],
        studio="VirtualReal",
        title="Scene.Title",
        resolution="1080p",
        is_vr=True,
    )
    assert name.endswith(".1080p.VR.mp4")
    assert parse_filename(name).is_vr is True


def test_build_vr_without_resolution():
    name = build_filename(
        actors=["Jane.Doe"],
        studio="VirtualReal",
        title="Scene.Title",
        resolution=None,
        is_vr=True,
    )
    assert name == "Jane.Doe.VirtualReal.Scene.Title.VR.mp4"
    p = parse_filename(name)
    assert p.resolution is None
    assert p.is_vr is True


def test_build_truncates_to_max_three_actors():
    name = build_filename(
        actors=["A.One", "B.Two", "C.Three", "D.Four"],
        studio="Studio",
        title="Title",
        resolution="720p",
    )
    p = parse_filename(name)
    assert len(p.actors) == 3


def test_reject_whitespace():
    with pytest.raises(ParseError):
        parse_filename("Jane Doe.Studio.Title.4k.mp4")


def test_accept_missing_resolution():
    p = parse_filename("Jane.Doe.Studio.Title.mp4")
    assert p.resolution is None
    assert p.studio == "Studio"
    assert p.title == "Title"


def test_reject_garbage():
    assert try_parse_filename("random-download.bin") is None
    with pytest.raises(ParseError):
        parse_filename("totally_wrong_name.mp4")


def test_build_truncates_title_for_length():
    long_title = ".".join(["Word"] * 40)
    name = build_filename(
        actors=["Jane.Doe"],
        studio="Studio",
        title=long_title,
        resolution="4k",
        max_length=150,
    )
    assert len(name) <= 150
    parse_filename(name)  # still valid


def test_resolution_from_dimensions():
    assert resolution_from_dimensions(3840, 2160) == "4k"
    assert resolution_from_dimensions(1920, 1080) == "1080p"
    assert resolution_from_dimensions(1280, 720) == "720p"
    assert resolution_from_dimensions(None, None) is None
    assert resolution_from_dimensions(320, 240) is None
