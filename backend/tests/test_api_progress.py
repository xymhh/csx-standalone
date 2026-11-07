from datetime import date, timedelta

from p4_helpers import login

from csx.infra.db import SessionLocal
from csx.infra.models import Episode, LibraryFile, MediaItem, Season


def test_progress_overview_and_single_media_matrix(client):
    login(client)
    with SessionLocal() as db:
        media = MediaItem(tmdb_id=987654321, type="tv", title="P4 progress")
        db.add(media)
        db.flush()
        season = Season(media_id=media.id, season_number=1, episode_count=2)
        db.add(season)
        db.flush()
        first = Episode(
            season_id=season.id, episode_number=1, air_date=date.today() - timedelta(days=1)
        )
        second = Episode(
            season_id=season.id, episode_number=2, air_date=date.today() + timedelta(days=1)
        )
        db.add_all([first, second])
        db.flush()
        db.add(LibraryFile(episode_id=first.id, path="/library/episode-1.mkv", size=1024))
        db.commit()
        media_id = media.id

    matrix = client.get(f"/api/v1/progress/{media_id}")
    assert matrix.status_code == 200
    data = matrix.json()["data"]
    assert data["aired_count"] == 1
    assert data["owned_count"] == 1
    assert data["missing"] == []
    assert len(data["seasons"][0]["episodes"]) == 2
    files = client.get(f"/api/v1/library/files?media_id={media_id}").json()["data"]
    assert files[0]["quality_bucket"] == "sd"
    assert client.get("/api/v1/library/servers").json()["data"][0]["provider"] == "emby"
    overview = client.get("/api/v1/progress").json()["data"]
    assert any(item["media_id"] == media_id for item in overview)
    assert client.get("/api/v1/progress/999999").status_code == 404
