from fastapi.testclient import TestClient

from csx.infra.db import SessionLocal
from csx.infra.models import Episode, LibraryFile, MediaItem, Season
from tests.p4_helpers import login


def test_api_duplicates_list_and_recommendation(client: TestClient):
    login(client)
    with SessionLocal() as db:
        m = MediaItem(title="庆余年", type="tv", tmdb_id=94954)
        db.add(m)
        db.flush()
        s = Season(media_id=m.id, season_number=1, episode_count=1)
        db.add(s)
        db.flush()
        ep = Episode(season_id=s.id, episode_number=1, title="第1集")
        db.add(ep)
        db.flush()

        # 录入一高一低两个版本
        f_hd = LibraryFile(
            episode_id=ep.id,
            path="庆余年 S01E01 1080p.mkv",
            size=1000,
            quality_bucket="hd",
            provider="quark",
        )
        f_remux = LibraryFile(
            episode_id=ep.id,
            path="庆余年 S01E01 REMUX.mkv",
            size=3000,
            quality_bucket="remux",
            provider="quark",
        )
        db.add_all([f_hd, f_remux])
        db.commit()
        hd_id = f_hd.id
        remux_id = f_remux.id

    res = client.get("/api/v1/library/duplicates")
    assert res.status_code == 200
    data = res.json().get("data", [])
    assert len(data) >= 1
    group = next(g for g in data if g["media_id"] == m.id)
    assert group["keep_file_id"] == remux_id

    files = group["files"]
    rec_file = next(f for f in files if f["recommended"])
    dup_file = next(f for f in files if not f["recommended"])
    assert rec_file["id"] == remux_id
    assert dup_file["id"] == hd_id
