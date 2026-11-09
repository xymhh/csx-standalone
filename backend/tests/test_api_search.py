from p4_helpers import login

from csx.adapters.search import executor


class _FakeService:
    def __init__(self, rows):
        self._rows = rows

    def search(self, query):
        if isinstance(self._rows, Exception):
            raise self._rows
        return self._rows


def _patch_services(monkeypatch, mapping):
    def fake_build(definition, config, context):
        return _FakeService(mapping.get(definition.id, []))

    monkeypatch.setattr(executor, "_build_search_service", fake_build)


def test_search_sources_lists_registered_channels(client):
    login(client)
    response = client.get("/api/v1/search/sources")
    assert response.status_code == 200
    sources = response.json()["data"]["sources"]
    assert len(sources) >= 10
    assert {"id", "name", "enabled", "order"} <= sources[0].keys()


def test_search_rejects_empty_keyword(client):
    login(client)
    response = client.get("/api/v1/search?q=")
    assert response.status_code == 422


def test_search_aggregates_and_normalizes_candidates(client, monkeypatch):
    login(client)
    mapping = {
        "mikan": [
            {
                "title": "[GM-Team][三体][01-15 Fin][1080P]",
                "url": "magnet:?xt=urn:btih:aaa",
                "resource_type": "magnet",
                "size": 2 * 1024**3,
                "pubdate": "2023/04/16 14:27",
                "fansub": "GM-Team",
            }
        ],
        "pansou": {
            "quark": [
                {
                    "title": "三体 全30集 4K",
                    "url": "https://pan.quark.cn/s/abc123",
                    "resource_type": "quark",
                    "update_time": "2024-01-02",
                    "password": "1234",
                }
            ]
        },
        "seedhub": RuntimeError("请先填写 SeedHub 地址"),
    }
    _patch_services(monkeypatch, mapping)

    payload = client.get("/api/v1/search?q=三体&limit=20").json()["data"]
    sources = {item["id"]: item for item in payload["sources"]}
    assert sources["mikan"]["status"] == "ok"
    assert sources["seedhub"]["status"] == "error"
    assert "未填写必要配置" in sources["seedhub"]["message"]

    items = {item["resource_type"]: item for item in payload["items"]}
    assert items["quark"]["can_transfer"] is True
    assert items["quark"]["password"] == "1234"
    assert items["quark"]["source"] == "pansou"
    assert items["magnet"]["can_transfer"] is False
    assert items["magnet"]["size_text"] == "2.0 GB"
    assert items["magnet"]["fansub"] == "GM-Team"


def test_search_respects_disabled_and_selected_sources(client, monkeypatch):
    login(client)
    client.put(
        "/api/v1/settings/sources",
        json={"mikan": {"enabled": False}},
    )
    _patch_services(
        monkeypatch,
        {
            "mikan": [{"title": "三体", "url": "magnet:?xt=urn:btih:bbb"}],
            "pansou": [{"title": "三体", "url": "https://pan.quark.cn/s/xyz"}],
        },
    )
    payload = client.get("/api/v1/search?q=三体").json()["data"]
    statuses = {item["id"]: item["status"] for item in payload["sources"]}
    assert statuses["mikan"] == "disabled"
    assert {item["source"] for item in payload["items"]} == {"pansou"}

    only_pansou = client.get("/api/v1/search?q=三体&sources=pansou").json()["data"]
    assert [item["id"] for item in only_pansou["sources"]] == ["pansou"]
