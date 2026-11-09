from __future__ import annotations

from datetime import date

import pytest

from csx.domain.naming import build_media_paths, parse_episode_from_name


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Show.S02E03.1080p.mkv", (2, 3)),
        ("Drama.S1EP9.WEB", (1, 9)),
        ("Movie 1080p EP12 BluRay", (None, 12)),
        ("Noise E 08 HDR", (None, 8)),
        ("动画 第2季第7集", (2, 7)),
        ("动画 第 12 集", (None, 12)),
        ("第3季第001集", (3, 1)),
        ("Title_s03_e04", (3, 4)),
        ("Title S09E101", (9, 101)),
        ("x.S00E00", (0, 0)),
        ("Movie.EP123", (None, 123)),
        ("Series EP 7 4K", (None, 7)),
        ("x 第10季 第20集", (10, 20)),
        ("2023-01-01 1080p", (None, None)),
        ("共3集", (None, None)),
        ("count 共 12 集", (None, None)),
        ("", (None, None)),
        ("plain title", (None, None)),
        ("S02E03-04", (2, 3)),
        ("[1080p] Episode 22", (None, 22)),
        ("10.mkv", (None, 10)),
        ("第08集.mp4", (None, 8)),
        ("2026 10.mkv", (None, None)),
    ],
)
def test_parse_episode_from_name(text, expected):
    assert parse_episode_from_name(text) == expected


def test_naming_tv_movie_variety_quality_and_cleaning():
    folder, filename = build_media_paths("A/B", "tv", 2024, 2, 3, "sd", ".mkv", "episode")
    assert (folder, filename) == ("A B (2024)/Season 02", "A B (2024) S02E03.mkv")
    assert build_media_paths("Film", "movie", 2020, None, None, "sd", "mp4", "movie") == (
        "Film (2020)",
        "Film (2020).mp4",
    )
    assert build_media_paths("Show", "tv", None, 1, 4, "sd", "mkv", "episode")[1] == (
        "Show S01E04.mkv"
    )
    assert "[DV]" in build_media_paths("Show", "tv", 2020, 1, 1, "dv", "mkv", "episode")[1]
    assert "[REMUX]" in build_media_paths("Show", "tv", 2020, 1, 1, "remux", "mkv", "episode")[1]
    assert "[HDR]" in build_media_paths("Show", "tv", 2020, 1, 1, "hdr", "mkv", "episode")[1]
    for bucket in ("sd", "hd", "4k", ""):
        assert "[" not in build_media_paths("Show", "tv", 2020, 1, 1, bucket, "mkv", "episode")[1]
    dated = build_media_paths(
        "Show 2024-05-06",
        "tv",
        2024,
        1,
        2,
        "hdr",
        "mkv",
        "variety",
        release_date=date(2024, 5, 6),
    )
    assert dated == (
        "Show 2024-05-06 (2024)",
        "Show 2024-05-06 - S01E02 (2024-05-06) [HDR].mkv",
    )
    assert build_media_paths("Show", "tv", 2024, 1, 2, "sd", "mkv", "variety") == (
        "Show (2024)",
        "Show - E02.mkv",
    )
    assert build_media_paths("Show 2024-05-06", "tv", None, 1, 2, "sd", "mkv", "variety")[1] == (
        "Show 2024-05-06 - E02.mkv"
    )
    folder, filename = build_media_paths("x" * 240, "movie", None, None, None, "sd", "mkv", "movie")
    assert len(folder) <= 200 and len(filename) <= 200
