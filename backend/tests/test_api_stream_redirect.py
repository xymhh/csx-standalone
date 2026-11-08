from fastapi.testclient import TestClient

from csx.api.routes.stream import _remember_url, clear_cache
from csx.infra.db import SessionLocal
from csx.infra.models import Episode, LibraryFile, MediaItem, Season


def test_stream_redirect_public_access_and_cache(client: TestClient):
    clear_cache()
    # 模拟库内已有文件
    with SessionLocal() as db:
        m = MediaItem(title="沙丘2", type="movie", tmdb_id=693134)
        db.add(m)
        db.flush()
        s = Season(media_id=m.id, season_number=1, episode_count=1)
        db.add(s)
        db.flush()
        ep = Episode(season_id=s.id, episode_number=1, title="正片")
        db.add(ep)
        db.flush()
        lf = LibraryFile(
            episode_id=ep.id,
            path="电影/沙丘2 (2024)/沙丘2.mkv",
            size=1024,
            quality_bucket="hdr",
            provider="quark",
        )
        db.add(lf)
        db.commit()
        file_id = lf.id

    # 预先向缓存写入一条模拟网盘直链
    fake_url = "https://cdn.quark.cn/download/test-stream-file.mkv?sign=123"
    _remember_url(file_id, "TestUA", fake_url)

    # 发起公开请求（不带登录 cookie，带 User-Agent）
    res = client.get(
        f"/api/v1/stream/redirect?file_id={file_id}",
        headers={"User-Agent": "TestUA"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers.get("location") == fake_url

    # 测试未命中文件返回 404
    res_404 = client.get("/api/v1/stream/redirect?file_id=999999", follow_redirects=False)
    assert res_404.status_code == 404
