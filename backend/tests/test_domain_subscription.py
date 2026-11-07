"""subscription.py 领域模型测试。"""

from __future__ import annotations

from datetime import date, timedelta

from csx.domain.media import Episode, EpisodeKey, Season
from csx.domain.subscription import (
    ScopeMode,
    SubscriptionScope,
    aired_episodes,
    missing_episodes,
    season_progress,
)


class TestScopeMode:
    def test_all_value(self):
        assert ScopeMode.ALL == "all"

    def test_range_value(self):
        assert ScopeMode.RANGE == "range"

    def test_latest_value(self):
        assert ScopeMode.LATEST == "latest"


class TestSubscriptionScopeFromJson:
    def test_none_returns_default(self):
        s = SubscriptionScope.from_json(None)
        assert s.mode == ScopeMode.ALL
        assert s.seasons == ()
        assert s.from_episode is None
        assert s.to_episode is None
        assert s.latest_count == 0

    def test_empty_string_returns_default(self):
        s = SubscriptionScope.from_json("")
        assert s.mode == ScopeMode.ALL

    def test_empty_dict_returns_default(self):
        s = SubscriptionScope.from_json({})
        assert s.mode == ScopeMode.ALL

    def test_invalid_json_string(self):
        s = SubscriptionScope.from_json("not json")
        assert s.mode == ScopeMode.ALL

    def test_invalid_mode_returns_all(self):
        s = SubscriptionScope.from_json({"mode": "invalid"})
        assert s.mode == ScopeMode.ALL

    def test_valid_all_mode(self):
        s = SubscriptionScope.from_json({"mode": "all"})
        assert s.mode == ScopeMode.ALL

    def test_valid_range_mode(self):
        s = SubscriptionScope.from_json({"mode": "range", "from_episode": 1, "to_episode": 10})
        assert s.mode == ScopeMode.RANGE
        assert s.from_episode == 1
        assert s.to_episode == 10

    def test_valid_latest_mode(self):
        s = SubscriptionScope.from_json({"mode": "latest", "latest_count": 5})
        assert s.mode == ScopeMode.LATEST
        assert s.latest_count == 5

    def test_seasons_dedup_sorted(self):
        s = SubscriptionScope.from_json({"seasons": [3, 1, 2, 1, 3]})
        assert s.seasons == (1, 2, 3)

    def test_negative_seasons_discarded(self):
        s = SubscriptionScope.from_json({"seasons": [1, -1, 2, -5]})
        assert s.seasons == (1, 2)

    def test_from_json_with_tuple_input(self):
        # 规格签名是 str | dict | None，list 不是合法类型，应回退默认
        s = SubscriptionScope.from_json([{"mode": "range"}])
        assert s.mode == ScopeMode.ALL  # list isn't allowed type, so returns default

    def test_field_order_preserved_in_output(self):
        s = SubscriptionScope.from_json({"mode": "range", "seasons": [3, 1], "from_episode": 5})
        json_str = s.to_json()
        # 检查字段顺序
        mode_idx = json_str.find('"mode"')
        seasons_idx = json_str.find('"seasons"')
        from_ep_idx = json_str.find('"from_episode"')
        assert mode_idx < seasons_idx < from_ep_idx


class TestSubscriptionScopeToJson:
    def test_to_json_stable(self):
        s = SubscriptionScope(
            mode=ScopeMode.RANGE, seasons=(1, 2), from_episode=1, to_episode=10, latest_count=0
        )
        json1 = s.to_json()
        json2 = s.to_json()
        assert json1 == json2

    def test_to_json_contains_fields(self):
        s = SubscriptionScope(mode=ScopeMode.LATEST, seasons=(5,), latest_count=3)
        json_str = s.to_json()
        assert '"mode":"latest"' in json_str
        assert '"seasons":[5]' in json_str
        assert '"latest_count":3' in json_str

    def test_to_json_compact(self):
        s = SubscriptionScope()
        json_str = s.to_json()
        # 不应有额外的空格
        assert ": " not in json_str


class TestSubscriptionScopeAccepts:
    def test_all_mode_accepts_any_episode(self):
        s = SubscriptionScope(mode=ScopeMode.ALL)
        assert s.accepts(EpisodeKey(1, 1))
        assert s.accepts(EpisodeKey(10, 50))

    def test_all_mode_season_filter_positive(self):
        s = SubscriptionScope(mode=ScopeMode.ALL, seasons=(2, 4))
        assert s.accepts(EpisodeKey(2, 1))
        assert s.accepts(EpisodeKey(4, 10))
        assert not s.accepts(EpisodeKey(1, 1))
        assert not s.accepts(EpisodeKey(3, 5))

    def test_range_mode_no_filter(self):
        s = SubscriptionScope(mode=ScopeMode.RANGE, from_episode=1, to_episode=10)
        assert s.accepts(EpisodeKey(1, 5))
        assert s.accepts(EpisodeKey(5, 5))
        assert s.accepts(EpisodeKey(100, 5))  # 季过滤为空，接受所有季

    def test_range_mode_with_season_filter(self):
        s = SubscriptionScope(mode=ScopeMode.RANGE, seasons=(1, 3), from_episode=5, to_episode=15)
        assert s.accepts(EpisodeKey(1, 10))
        assert s.accepts(EpisodeKey(3, 12))
        assert not s.accepts(EpisodeKey(2, 10))
        assert not s.accepts(EpisodeKey(1, 3))  # episode < from_episode
        assert not s.accepts(EpisodeKey(1, 20))  # episode > to_episode

    def test_range_mode_no_from_episode(self):
        s = SubscriptionScope(mode=ScopeMode.RANGE, to_episode=10)
        assert s.accepts(EpisodeKey(1, 1))
        assert s.accepts(EpisodeKey(1, 10))
        assert not s.accepts(EpisodeKey(1, 11))

    def test_range_mode_no_to_episode(self):
        s = SubscriptionScope(mode=ScopeMode.RANGE, from_episode=10)
        assert s.accepts(EpisodeKey(1, 10))
        assert s.accepts(EpisodeKey(1, 20))
        assert not s.accepts(EpisodeKey(1, 9))

    def test_latest_mode_basic(self):
        s = SubscriptionScope(mode=ScopeMode.LATEST, latest_count=5)
        assert s.accepts(EpisodeKey(1, 1))
        assert s.accepts(EpisodeKey(1, 100))


class TestAiredEpisodes:
    def test_air_date_none_is_aired(self):
        seasons = [
            Season(
                number=1,
                episodes=[
                    Episode(key=EpisodeKey(1, 1)),
                    Episode(key=EpisodeKey(1, 2), air_date=None),
                ],
            )
        ]
        result = aired_episodes(seasons)
        assert len(result) == 2

    def test_past_air_date_is_aired(self):
        today = date.today()
        past = today - timedelta(days=1)
        seasons = [Season(number=1, episodes=[Episode(key=EpisodeKey(1, 1), air_date=past)])]
        result = aired_episodes(seasons)
        assert len(result) == 1

    def test_future_air_date_not_aired(self):
        today = date.today()
        future = today + timedelta(days=1)
        seasons = [Season(number=1, episodes=[Episode(key=EpisodeKey(1, 1), air_date=future)])]
        result = aired_episodes(seasons)
        assert len(result) == 0

    def test_multiple_seasons(self):
        seasons = [
            Season(
                number=1,
                episodes=[
                    Episode(key=EpisodeKey(1, 1)),
                    Episode(key=EpisodeKey(1, 2), air_date=date.today() - timedelta(days=1)),
                ],
            ),
            Season(
                number=2,
                episodes=[Episode(key=EpisodeKey(2, 1), air_date=date.today() + timedelta(days=1))],
            ),
        ]
        result = aired_episodes(seasons)
        assert len(result) == 2

    def test_sorting_and_dedup(self):
        e1a = Episode(key=EpisodeKey(1, 1))
        e1b = Episode(key=EpisodeKey(1, 1))  # duplicate key
        seasons = [Season(number=1, episodes=[e1a, e1b, Episode(key=EpisodeKey(1, 2))])]
        result = aired_episodes(seasons)
        assert len(result) == 2
        assert result[0] == EpisodeKey(1, 1)
        assert result[1] == EpisodeKey(1, 2)


class TestMissingEpisodes:
    def test_missing_simple(self):
        seasons = [
            Season(
                number=1,
                episodes=[
                    Episode(key=EpisodeKey(1, 1)),
                    Episode(key=EpisodeKey(1, 2)),
                    Episode(key=EpisodeKey(1, 3)),
                ],
            )
        ]
        owned = {EpisodeKey(1, 1)}
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        result = missing_episodes(seasons, owned, scope)
        assert len(result) == 2
        assert EpisodeKey(1, 2) in result
        assert EpisodeKey(1, 3) in result

    def test_missing_sorted(self):
        seasons = [Season(number=1, episodes=[Episode(key=EpisodeKey(1, i)) for i in range(1, 11)])]
        owned = {EpisodeKey(1, 1), EpisodeKey(1, 3), EpisodeKey(1, 5)}
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        result = missing_episodes(seasons, owned, scope)
        assert result == [
            EpisodeKey(1, 2),
            EpisodeKey(1, 4),
            EpisodeKey(1, 6),
            EpisodeKey(1, 7),
            EpisodeKey(1, 8),
            EpisodeKey(1, 9),
            EpisodeKey(1, 10),
        ]

    def test_missing_with_owned_filter(self):
        seasons = [Season(number=1, episodes=[Episode(key=EpisodeKey(1, i)) for i in range(1, 6)])]
        owned = {EpisodeKey(1, 2), EpisodeKey(1, 4)}
        scope = SubscriptionScope(mode=ScopeMode.RANGE, from_episode=2, to_episode=4)
        result = missing_episodes(seasons, owned, scope)
        # RANGE 接受 2-4，owned 有 2 和 4，所以只缺 3
        assert result == [EpisodeKey(1, 3)]

    def test_missing_respects_unaired(self):
        today = date.today()
        past = today - timedelta(days=1)
        future = today + timedelta(days=1)
        seasons = [
            Season(
                number=1,
                episodes=[
                    Episode(key=EpisodeKey(1, 1), air_date=past),
                    Episode(key=EpisodeKey(1, 2), air_date=future),
                ],
            )
        ]
        owned = set()
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        result = missing_episodes(seasons, owned, scope)
        assert len(result) == 1
        assert result[0] == EpisodeKey(1, 1)

    def test_missing_duplicates_removed(self):
        e1a = Episode(key=EpisodeKey(1, 1))
        e1b = Episode(key=EpisodeKey(1, 1))  # duplicate
        seasons = [Season(number=1, episodes=[e1a, e1b, Episode(key=EpisodeKey(1, 2))])]
        owned = set()
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        result = missing_episodes(seasons, owned, scope)
        assert len(result) == 2


class TestSeasonProgress:
    def test_progress_basic(self):
        seasons = [Season(number=1, episodes=[Episode(key=EpisodeKey(1, i)) for i in range(1, 11)])]
        owned = {EpisodeKey(1, i) for i in range(1, 6)}
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        progress = season_progress(seasons, owned, scope)
        assert progress == {1: (5, 10)}

    def test_progress_zero_episodes(self):
        seasons = [Season(number=1, episodes=[])]
        owned = set()
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        progress = season_progress(seasons, owned, scope)
        assert progress == {1: (0, 0)}

    def test_progress_with_unaired(self):
        today = date.today()
        past = today - timedelta(days=1)
        seasons = [
            Season(
                number=1,
                episodes=[
                    Episode(key=EpisodeKey(1, 1), air_date=past),
                    Episode(key=EpisodeKey(1, 2), air_date=today + timedelta(days=1)),
                ],
            )
        ]
        owned = {EpisodeKey(1, 1)}
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        progress = season_progress(seasons, owned, scope)
        assert progress == {1: (1, 1)}

    def test_progress_respects_scope(self):
        seasons = [Season(number=1, episodes=[Episode(key=EpisodeKey(1, i)) for i in range(1, 11)])]
        owned = {EpisodeKey(1, i) for i in range(1, 6)}
        scope = SubscriptionScope(mode=ScopeMode.RANGE, from_episode=3, to_episode=7)
        progress = season_progress(seasons, owned, scope)
        # RANGE 接受 3-7（共 5 集），owned 有 3,4,5（共 3 集）
        assert progress == {1: (3, 5)}

    def test_progress_empty_seasons(self):
        seasons = []
        owned = set()
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        progress = season_progress(seasons, owned, scope)
        assert progress == {}

    def test_progress_multiple_seasons(self):
        seasons = [
            Season(number=1, episodes=[Episode(key=EpisodeKey(1, i)) for i in range(1, 6)]),
            Season(number=2, episodes=[Episode(key=EpisodeKey(2, i)) for i in range(1, 11)]),
        ]
        owned = {EpisodeKey(1, i) for i in range(1, 4)} | {EpisodeKey(2, i) for i in range(1, 6)}
        scope = SubscriptionScope(mode=ScopeMode.ALL)
        progress = season_progress(seasons, owned, scope)
        assert progress == {1: (3, 5), 2: (5, 10)}
