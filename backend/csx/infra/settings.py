"""运行时配置，全部可用 CSX_ 前缀的环境变量覆盖。"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CSX_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]
    web_dist: Path = Path("web/dist")

    # 鉴权
    admin_user: str = "admin"
    admin_password: str = ""
    cookie_secure: bool = False
    session_ttl_days: int = 7
    login_max_attempts: int = 5
    login_window_seconds: int = 900


settings = Settings()
