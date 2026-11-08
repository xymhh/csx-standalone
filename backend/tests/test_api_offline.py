from fastapi.testclient import TestClient

from csx.infra.db import SessionLocal
from csx.infra.models import Account
from tests.p4_helpers import login


class Fake115OfflineDrive:
    def list_offline_tasks(self):
        return [
            {
                "id": "HASH123",
                "name": "测试磁力下载任务.mkv",
                "size": 2048000,
                "state": "running",
                "status_text": "下载中",
                "percent": 45.5,
                "add_time": 1700000000,
            }
        ]

    def add_offline_task(self, url: str, parent_id: str = "0"):
        return {"state": True, "info_hash": "NEW_HASH"}

    def delete_offline_tasks(self, hashes: list[str]):
        return True


def test_api_offline_flow(client: TestClient):
    login(client)
    with SessionLocal() as db:
        acc = Account(provider="115", name="我的115", credential="dummy_cookie_val")
        db.add(acc)
        db.commit()
        account_id = acc.id

    client.app.state.drives = {"115": Fake115OfflineDrive()}

    # 1. 查询离线任务
    res = client.get(f"/api/v1/drives/offline/tasks?account_id={account_id}")
    assert res.status_code == 200
    tasks = res.json().get("data", [])
    assert len(tasks) == 1
    assert tasks[0]["id"] == "HASH123"
    assert tasks[0]["percent"] == 45.5

    # 2. 添加离线任务
    add_res = client.post(
        "/api/v1/drives/offline/add",
        json={"account_id": account_id, "url": "magnet:?xt=urn:btih:dummy123"},
    )
    assert add_res.status_code == 200
    assert add_res.json().get("data", {}).get("state") is True

    # 3. 删除离线任务
    del_res = client.post(
        "/api/v1/drives/offline/delete",
        json={"account_id": account_id, "hashes": ["HASH123"]},
    )
    assert del_res.status_code == 200
    assert del_res.json().get("data", {}).get("deleted") is True

    # 清理测试数据
    with SessionLocal() as db:
        row = db.get(Account, account_id)
        if row:
            db.delete(row)
            db.commit()
