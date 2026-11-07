from datetime import date

from p4_helpers import login

from csx.infra.db import SessionLocal
from csx.infra.models import Episode, LibraryFile, MediaItem, Season


def test_progress_detail_includes_metadata_and_owned_file_details(client):
    login(client)
    with SessionLocal() as db:
        media = MediaItem(
            tmdb_id=99202411,
            type="tv",
            title="Drawer detail",
            year=2024,
            overview="A test synopsis",
            poster_url="https://example.invalid/poster.jpg",
        )
        db.add(media)
        db.flush()
        season = Season(media_id=media.id, season_number=1, episode_count=1)
        db.add(season)
        db.flush()
        episode = Episode(season_id=season.id, episode_number=1, air_date=date(2024, 1, 1))
        db.add(episode)
        db.flush()
        file = LibraryFile(
            episode_id=episode.id,
            path="/media/Drawer.detail.S01E01.1080p.mkv",
            size=1234,
            quality_bucket="hd",
        )
        db.add(file)
        db.commit()
        media_id = media.id
        file_id = file.id

    response = client.get(f"/api/v1/progress/{media_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert (data["year"], data["overview"], data["poster_url"]) == (
        2024,
        "A test synopsis",
        "https://example.invalid/poster.jpg",
    )
    detail = data["seasons"][0]["episodes"][0]["file"]
    assert detail["file_id"] == file_id
    assert detail["path"].endswith(".mkv")
    assert detail["size"] == 1234
    assert detail["quality_bucket"] == "hd"
