from fastapi.testclient import TestClient

from csx.adapters.media.tmdb import TmdbClient
from tests.p4_helpers import login


def test_tmdb_api_mocked(client: TestClient, monkeypatch):
    login(client)

    fake_trending = [
        {
            "id": 12345,
            "title": "测试热门影视",
            "type": "tv",
            "year": 2024,
            "release_date": "2024-05-01",
            "vote_average": 8.5,
            "overview": "测试简介描述",
            "poster_url": "https://image.tmdb.org/t/p/w500/test.jpg",
            "backdrop_url": "https://image.tmdb.org/t/p/w1280/back.jpg",
            "popularity": 100,
        }
    ]

    monkeypatch.setattr(TmdbClient, "get_trending", classmethod(lambda cls: fake_trending))
    monkeypatch.setattr(TmdbClient, "get_popular_tv", classmethod(lambda cls: fake_trending))
    monkeypatch.setattr(TmdbClient, "get_popular_movies", classmethod(lambda cls: fake_trending))
    monkeypatch.setattr(TmdbClient, "search", classmethod(lambda cls, q: fake_trending))
    monkeypatch.setattr(TmdbClient, "get_detail", classmethod(lambda cls, t, i: fake_trending[0]))

    # 1. Trending
    r1 = client.get("/api/v1/tmdb/trending")
    assert r1.status_code == 200
    assert r1.json()["data"][0]["title"] == "测试热门影视"

    # 2. Popular TV
    r2 = client.get("/api/v1/tmdb/popular/tv")
    assert r2.status_code == 200
    assert r2.json()["data"][0]["vote_average"] == 8.5

    # 3. Search
    r3 = client.get("/api/v1/tmdb/search?query=测试")
    assert r3.status_code == 200
    assert len(r3.json()["data"]) == 1

    # 4. Detail
    r4 = client.get("/api/v1/tmdb/detail/tv/12345")
    assert r4.status_code == 200
    assert r4.json()["data"]["id"] == 12345
