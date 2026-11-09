"""运行时配置。

优先级（高 → 低）：环境变量（`CSX_` 前缀）→ 工作目录 `.env` → `config.json` → 代码默认值。
`config.json` 路径由 `CSX_CONFIG_FILE` 指定，默认 `/config/config.json`（对齐 MoviePilot 的 `/config` 目录习惯）。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

CONFIG_FILE = Path(os.environ.get("CSX_CONFIG_FILE") or "/config/config.json")


class JsonConfigSource(PydanticBaseSettingsSource):
    """从 JSON 文件读配置；文件缺失或损坏时静默回退到下一级来源。"""

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        if not CONFIG_FILE.is_file():
            return {}
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CSX_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]
    web_dist: Path = Path("web/dist")
    transfer_root: str = "CSX"
    library_root: str = ""
    secret_key: str = ""
    tmdb_api_key: str = ""

    # 鉴权
    admin_user: str = "admin"
    admin_password: str = ""
    cookie_secure: bool = False
    session_ttl_days: int = 7
    login_max_attempts: int = 5
    login_window_seconds: int = 900

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            JsonConfigSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
