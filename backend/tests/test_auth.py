from tests.conftest import PASSWORD

USERNAME = "admin"


def _login(client, password: str = PASSWORD, username: str = USERNAME):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_login_bad_password(client) -> None:
    resp = _login(client, "wrong-password")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "BAD_CREDENTIALS"


def test_login_unknown_user(client) -> None:
    resp = _login(client, PASSWORD, "nobody")
    assert resp.status_code == 401


def test_login_success_sets_httponly_cookie(client) -> None:
    resp = _login(client)
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == USERNAME
    cookie = resp.headers["set-cookie"].lower()
    assert "csx_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_protected_route_after_login(client) -> None:
    client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
    resp = client.get("/api/v1/meta")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "CloudSubscribeX"


def test_me_returns_username(client) -> None:
    client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == USERNAME


def test_logout_invalidates_session(client) -> None:
    client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
    assert client.get("/api/v1/meta").status_code == 200

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert client.get("/api/v1/meta").status_code == 401


def test_change_password_rejects_wrong_old(client) -> None:
    client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
    resp = client.post(
        "/api/v1/auth/password",
        json={"old_password": "not-the-password", "new_password": "new-password-123"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_OLD_PASSWORD"


def test_change_password_roundtrip(client) -> None:
    new_password = "brand-new-password-456"
    client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
    resp = client.post(
        "/api/v1/auth/password",
        json={"old_password": PASSWORD, "new_password": new_password},
    )
    assert resp.status_code == 200
    # 改密后旧会话失效
    assert client.get("/api/v1/meta").status_code == 401
    # 新密码可登录
    assert _login(client, new_password).status_code == 200
    # 还原
    client.post(
        "/api/v1/auth/password",
        json={"old_password": new_password, "new_password": PASSWORD},
    )


def test_rate_limit_blocks_after_failures(client) -> None:
    for _ in range(5):
        assert _login(client, "wrong").status_code == 401
    resp = _login(client, "wrong")
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
