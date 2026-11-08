from p4_helpers import login

from csx.domain.naming import DEFAULT_MOVIE_TEMPLATE, DEFAULT_TV_TEMPLATE


def test_naming_defaults_and_variables(client):
    login(client)
    data = client.get("/api/v1/naming").json()["data"]
    assert data["defaults"]["movie_format"] == DEFAULT_MOVIE_TEMPLATE
    assert data["defaults"]["tv_format"] == DEFAULT_TV_TEMPLATE
    assert {item["name"] for item in data["variables"]} >= {
        "title",
        "year",
        "season_episode",
        "fileExt",
        "videoFormat",
    }


def test_naming_save_validates_and_persists(client):
    login(client)
    custom_movie = "{{title}}/{{title}} [{{videoFormat}}]{{fileExt}}"
    custom_tv = "{{title}}/S{{season}}/{{title}} {{season_episode}}{{fileExt}}"
    saved = client.put(
        "/api/v1/naming",
        json={"movie_format": custom_movie, "tv_format": custom_tv, "variety_format": ""},
    )
    assert saved.status_code == 200
    data = saved.json()["data"]
    assert data["movie_format"] == custom_movie
    assert data["tv_format"] == custom_tv
    assert data["variety_format"] == custom_tv

    current = client.get("/api/v1/naming").json()["data"]
    assert current["movie_format"] == custom_movie

    restored = client.put(
        "/api/v1/naming",
        json={
            "movie_format": DEFAULT_MOVIE_TEMPLATE,
            "tv_format": DEFAULT_TV_TEMPLATE,
            "variety_format": "",
        },
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["movie_format"] == DEFAULT_MOVIE_TEMPLATE


def test_naming_rejects_template_without_directory(client):
    login(client)
    response = client.put(
        "/api/v1/naming",
        json={"movie_format": "{{title}}{{fileExt}}", "tv_format": DEFAULT_TV_TEMPLATE},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NAMING_TEMPLATE_INVALID"


def test_naming_preview_returns_relative_path_and_warnings(client):
    login(client)
    good = client.post(
        "/api/v1/naming/preview",
        json={
            "media_type": "tv",
            "title": "示例剧集",
            "year": 2024,
            "season": 2,
            "episode": 3,
            "extension": "mkv",
            "quality_bucket": "4k",
        },
    ).json()["data"]
    assert good["valid"] is True
    assert good["relative_path"] == "示例剧集 (2024)/Season 2/示例剧集 - S02E03 - 第 3 集.mkv"

    bad = client.post(
        "/api/v1/naming/preview",
        json={"media_type": "movie", "title": "示例电影", "template": "{{title}}"},
    ).json()["data"]
    assert bad["valid"] is False
    assert "目录" in bad["message"]
