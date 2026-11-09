from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from csx.adapters.media import anilist, bangumi, douban
from tests.p4_helpers import login


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _clear_rank_caches():
    douban._cache.clear()
    bangumi._cache.clear()
    anilist._cache.clear()
    yield
    douban._cache.clear()
    bangumi._cache.clear()
    anilist._cache.clear()


def test_douban_parses_subjects(monkeypatch):
    seen = {}

    def fake_get(url, headers=None, impersonate=None, timeout=None):
        seen["url"] = url
        seen["headers"] = headers
        seen["impersonate"] = impersonate
        return FakeResponse(
            {
                "subjects": [
                    {
                        "id": "123",
                        "title": "测试电影 (2024)",
                        "rate": "8.6",
                        "cover": "https://img.example/douban.jpg",
                    },
                    {"id": "456", "title": "无年份电影", "rate": "", "cover": ""},
                ]
            }
        )

    monkeypatch.setattr(douban.requests, "get", fake_get)

    items = douban.get_rank("showing")

    assert len(items) == 2
    assert items[0] == {
        "id": -123,
        "title": "测试电影 (2024)",
        "type": "movie",
        "year": 2024,
        "release_date": "",
        "vote_average": 8.6,
        "overview": "",
        "poster_url": "https://img.example/douban.jpg",
        "backdrop_url": None,
    }
    assert items[1]["id"] == -456
    assert items[1]["year"] is None
    assert items[1]["vote_average"] == 0.0
    assert items[1]["poster_url"] is None
    assert "type=movie" in seen["url"]
    assert "tag=正在热映" in seen["url"]
    assert seen["impersonate"] == "chrome"
    assert "Chrome" in seen["headers"]["User-Agent"]


def test_douban_error_returns_empty(monkeypatch):
    def fake_get(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(douban.requests, "get", fake_get)

    assert douban.get_rank("movie_hot") == []


def test_douban_cache_hit_avoids_second_request(monkeypatch):
    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse({"subjects": [{"id": "1", "title": "缓存电影", "rate": "7.0"}]})

    monkeypatch.setattr(douban.requests, "get", fake_get)

    first = douban.get_rank("tv_hot")
    second = douban.get_rank("tv_hot")

    assert first == second
    assert calls["count"] == 1


def test_bangumi_merges_dedupes_and_sorts(monkeypatch):
    seen = {}

    def fake_get(url, headers=None, timeout=None):
        seen["headers"] = headers
        return FakeResponse(
            [
                {
                    "weekday": {"id": 1},
                    "items": [
                        {
                            "id": 11,
                            "name": "A",
                            "name_cn": "甲",
                            "air_date": "2024-04-01",
                            "rating": {"score": 8.0},
                            "images": {"large": "https://img.example/a.jpg"},
                            "summary": "甲" * 300,
                        },
                        {
                            "id": 12,
                            "name": "B",
                            "name_cn": "",
                            "air_date": "",
                            "rating": {"score": 7.5},
                            "images": {},
                            "summary": "乙",
                        },
                    ],
                },
                {
                    "weekday": {"id": 2},
                    "items": [
                        {
                            "id": 11,
                            "name": "A",
                            "name_cn": "甲",
                            "air_date": "2024-04-01",
                            "rating": {"score": 8.0},
                            "images": {"large": "https://img.example/a.jpg"},
                            "summary": "重复条目",
                        },
                        {
                            "id": 13,
                            "name": "C",
                            "name_cn": "丙",
                            "air_date": "2023-10-01",
                            "rating": {"score": 9.2},
                            "images": {"large": "https://img.example/c.jpg"},
                            "summary": "丙",
                        },
                    ],
                },
            ]
        )

    monkeypatch.setattr(bangumi.requests, "get", fake_get)

    items = bangumi.get_calendar()

    assert [item["id"] for item in items] == [-13, -11, -12]
    assert items[0]["vote_average"] == 9.2
    assert items[0]["type"] == "tv"
    assert items[0]["year"] == 2023
    assert items[0]["title"] == "丙"
    assert len(items[1]["overview"]) == 200
    assert items[2]["title"] == "B"
    assert items[2]["year"] is None
    assert items[2]["poster_url"] is None
    assert seen["headers"]["User-Agent"] == bangumi.BANGUMI_UA
    assert "csx-standalone" in seen["headers"]["User-Agent"]


@pytest.mark.parametrize(
    ("month", "expected"),
    [
        (1, "WINTER"),
        (3, "SPRING"),
        (7, "SUMMER"),
        (10, "FALL"),
        (12, "WINTER"),
    ],
)
def test_anilist_month_to_season(month, expected):
    assert anilist.season_for_month(month) == expected


def test_anilist_parses_media(monkeypatch):
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen["url"] = url
        seen["json"] = json
        return FakeResponse(
            {
                "data": {
                    "Page": {
                        "media": [
                            {
                                "id": 99,
                                "title": {"romaji": "Romaji", "native": "日本語"},
                                "coverImage": {"extraLarge": "https://img.example/anilist.jpg"},
                                "averageScore": 87,
                                "seasonYear": 2026,
                                "format": "TV",
                            }
                        ]
                    }
                }
            }
        )

    monkeypatch.setattr(anilist.requests, "post", fake_post)

    items = anilist.get_season(month=4)

    assert seen["url"] == anilist.ANILIST_GRAPHQL_URL
    assert seen["json"]["variables"] == {"season": "SPRING", "year": datetime.now().year}
    assert items == [
        {
            "id": -99,
            "title": "日本語",
            "type": "tv",
            "year": 2026,
            "release_date": "",
            "vote_average": 8.7,
            "overview": "",
            "poster_url": "https://img.example/anilist.jpg",
            "backdrop_url": None,
        }
    ]


def test_douban_route_rejects_invalid_rank(client: TestClient):
    login(client)

    response = client.get("/api/v1/tmdb/douban/not-a-rank")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RANK"


def test_douban_route_returns_items(client: TestClient, monkeypatch):
    login(client)
    fake_items = [{"id": -1, "title": "榜单条目", "type": "movie"}]
    monkeypatch.setattr(douban, "get_rank", lambda rank: fake_items)

    response = client.get("/api/v1/tmdb/douban/tv_hot")

    assert response.status_code == 200
    assert response.json()["data"] == fake_items
