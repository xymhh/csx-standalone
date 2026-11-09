"""海报代理路由测试。"""

from __future__ import annotations

from types import SimpleNamespace

import csx.api.routes.media as media_route


def test_poster_rejects_unknown_host(client):
    resp = client.get("/api/v1/media/poster", params={"url": "https://evil.example.com/a.jpg"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "POSTER_HOST_NOT_ALLOWED"


def test_poster_rejects_http_scheme(client):
    resp = client.get(
        "/api/v1/media/poster",
        params={"url": "http://img3.doubanio.com/view/photo/a.jpg"},
    )
    assert resp.status_code == 400


def test_poster_forwards_with_referer(client, monkeypatch):
    captured: dict[str, object] = {}

    def fake_get(url, headers=None, impersonate=None, timeout=None):
        captured["url"] = url
        captured["referer"] = (headers or {}).get("Referer")
        return SimpleNamespace(
            status_code=200, content=b"fake-jpeg", headers={"content-type": "image/jpeg"}
        )

    monkeypatch.setattr(media_route.requests, "get", fake_get)
    resp = client.get(
        "/api/v1/media/poster",
        params={"url": "https://img3.doubanio.com/view/photo/a.jpg"},
    )
    assert resp.status_code == 200
    assert resp.content == b"fake-jpeg"
    assert captured["referer"] == "https://movie.douban.com/"


def test_poster_returns_404_when_upstream_fails(client, monkeypatch):
    def fake_get(url, headers=None, impersonate=None, timeout=None):
        return SimpleNamespace(status_code=418, content=b"", headers={})

    monkeypatch.setattr(media_route.requests, "get", fake_get)
    resp = client.get(
        "/api/v1/media/poster",
        params={"url": "https://img3.doubanio.com/view/photo/a.jpg"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "POSTER_NOT_FOUND"
