from __future__ import annotations

import json
import os

import pytest

import csx.infra.settings as settings_module


@pytest.fixture(autouse=True)
def _clear_csx_env(monkeypatch):
    """隔离测试环境里已有的 CSX_* 变量（conftest 会设置数据目录）。"""
    for key in list(os.environ):
        if key.startswith("CSX_"):
            monkeypatch.delenv(key, raising=False)


def _use_config(monkeypatch, tmp_path, data: dict[str, object]):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("CSX_CONFIG_FILE", str(config_file))
    monkeypatch.setattr(settings_module, "CONFIG_FILE", config_file)
    return settings_module.Settings()


def test_json_config_is_read(monkeypatch, tmp_path):
    settings = _use_config(
        monkeypatch,
        tmp_path,
        {
            "data_dir": str(tmp_path / "data"),
            "admin_user": "tester",
            "cookie_secure": True,
            "session_ttl_days": 3,
        },
    )
    assert settings.admin_user == "tester"
    assert settings.cookie_secure is True
    assert settings.session_ttl_days == 3
    assert str(settings.data_dir) == str(tmp_path / "data")


def test_env_overrides_json(monkeypatch, tmp_path):
    monkeypatch.setenv("CSX_ADMIN_USER", "from_env")
    settings = _use_config(monkeypatch, tmp_path, {"admin_user": "from_json"})
    assert settings.admin_user == "from_env"


def test_missing_file_falls_back_to_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module, "CONFIG_FILE", tmp_path / "missing.json")
    settings = settings_module.Settings()
    assert settings.admin_user == "admin"
    assert settings.data_dir.name == "data"


def test_broken_json_falls_back_to_defaults(monkeypatch, tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(settings_module, "CONFIG_FILE", broken)
    settings = settings_module.Settings()
    assert settings.admin_user == "admin"


def test_non_object_json_is_ignored(monkeypatch, tmp_path):
    weird = tmp_path / "list.json"
    weird.write_text('["a", "b"]', encoding="utf-8")
    monkeypatch.setattr(settings_module, "CONFIG_FILE", weird)
    settings = settings_module.Settings()
    assert settings.admin_user == "admin"
