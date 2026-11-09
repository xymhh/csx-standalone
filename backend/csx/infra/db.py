"""SQLite 连接与会话工厂。"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from csx.infra.settings import settings

settings.data_dir.mkdir(parents=True, exist_ok=True)
DB_PATH = settings.data_dir / "csx.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 30},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
