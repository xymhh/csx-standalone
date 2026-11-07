"""media.py 领域模型测试。"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from csx.domain.media import Episode, EpisodeKey, MediaItem, MediaType, Season


class TestMediaType:
    def test_tv_value(self):
        assert MediaType.TV == "tv"

    def test_movie_value(self):
        assert MediaType.MOVIE == "movie"


class TestEpisodeKey:
    def test_str_padding_small(self):
        key = EpisodeKey(season=1, episode=2)
        assert str(key) == "S01E02"

    def test_str_padding_medium(self):
        key = EpisodeKey(season=10, episode=100)
        assert str(key) == "S10E100"

    def test_str_padding_large(self):
        key = EpisodeKey(season=12, episode=108)
        assert str(key) == "S12E108"

    def test_sorting_earlier_season(self):
        k1 = EpisodeKey(season=1, episode=5)
        k2 = EpisodeKey(season=2, episode=1)
        assert k1 < k2

    def test_sorting_same_season_later_episode(self):
        k1 = EpisodeKey(season=1, episode=5)
        k2 = EpisodeKey(season=1, episode=10)
        assert k1 < k2

    def test_sorting_same(self):
        k1 = EpisodeKey(season=1, episode=5)
        k2 = EpisodeKey(season=1, episode=5)
        assert k1 == k2
        assert not (k1 < k2)
        assert not (k2 < k1)


class TestEpisode:
    def test_frozen(self):
        ep = Episode(key=EpisodeKey(1, 1), title="Test")
        with pytest.raises(FrozenInstanceError):
            ep.title = "New"

    def test_default_air_date_none(self):
        ep = Episode(key=EpisodeKey(1, 1))
        assert ep.air_date is None

    def test_default_title_empty(self):
        ep = Episode(key=EpisodeKey(1, 1))
        assert ep.title == ""

    def test_with_all_fields(self):
        from datetime import date

        ep = Episode(key=EpisodeKey(1, 1), air_date=date(2024, 1, 1), title="Intro")
        assert ep.air_date == date(2024, 1, 1)
        assert ep.title == "Intro"


class TestSeason:
    def test_default_episodes_empty_tuple(self):
        s = Season(number=1)
        assert s.episodes == ()

    def test_with_episodes(self):

        e1 = Episode(key=EpisodeKey(1, 1))
        e2 = Episode(key=EpisodeKey(1, 2))
        s = Season(number=1, episodes=(e1, e2))
        assert s.number == 1
        assert len(s.episodes) == 2


class TestMediaItem:
    def test_minimal(self):
        item = MediaItem(tmdb_id=123, type=MediaType.TV, title="Show")
        assert item.tmdb_id == 123
        assert item.type == MediaType.TV
        assert item.title == "Show"
        assert item.year is None
        assert item.seasons == ()

    def test_full(self):
        from datetime import date

        e = Episode(key=EpisodeKey(1, 1), air_date=date(2024, 1, 1))
        s = Season(number=1, episodes=(e,))
        item = MediaItem(tmdb_id=456, type=MediaType.MOVIE, title="Movie", year=2023, seasons=(s,))
        assert item.tmdb_id == 456
        assert item.year == 2023
        assert len(item.seasons) == 1

    def test_frozen(self):
        item = MediaItem(tmdb_id=789, type=MediaType.TV, title="X")
        with pytest.raises(FrozenInstanceError):
            item.tmdb_id = 999
