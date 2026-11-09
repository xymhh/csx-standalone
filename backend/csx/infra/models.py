"""SQLAlchemy table definitions for authentication and P1 business data."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AdminUser(Base):
    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuthSession(Base):
    __tablename__ = "auth_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("admin_user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="")


class MediaItem(Base):
    __tablename__ = "media_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer)
    overview: Mapped[str] = mapped_column(Text, default="", nullable=False)
    poster_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Season(Base):
    __tablename__ = "season"
    __table_args__ = (UniqueConstraint("media_id", "season_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media_item.id", ondelete="CASCADE"), nullable=False, index=True
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Episode(Base):
    __tablename__ = "episode"
    __table_args__ = (UniqueConstraint("season_id", "episode_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id", ondelete="CASCADE"), nullable=False, index=True
    )
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    air_date: Mapped[date | None] = mapped_column(Date)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Subscription(Base):
    __tablename__ = "subscription"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media_item.id"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    quality_pref: Mapped[str] = mapped_column(
        Text, default='{"min_bucket":"1080p"}', nullable=False
    )
    state: Mapped[str] = mapped_column(String, default="active", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, default="manual", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class DiscoveredResource(Base):
    __tablename__ = "discovered_resource"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscription.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    share_url: Mapped[str] = mapped_column(Text, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String)
    score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    state: Mapped[str] = mapped_column(String, default="new", nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class TransferTask(Base):
    __tablename__ = "transfer_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscription.id"), index=True)
    resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("discovered_resource.id"), index=True
    )
    state: Mapped[str] = mapped_column(String, default="queued", nullable=False, index=True)
    # 进行中的阶段文案（checking/transferring/relaying/organizing），终态清空
    stage: Mapped[str] = mapped_column(String, default="", nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    dead_letter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class ManualTransfer(Base):
    """Provider-specific payload for a standalone queued share transfer."""

    __tablename__ = "manual_transfer"

    task_id: Mapped[int] = mapped_column(
        ForeignKey("transfer_task.id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False)
    share_url: Mapped[str] = mapped_column(Text, nullable=False)
    password: Mapped[str] = mapped_column(Text, default="", nullable=False)
    file_ids: Mapped[str] = mapped_column(Text, nullable=False)
    target_dir: Mapped[str] = mapped_column(Text, nullable=False)
    media_id: Mapped[int | None] = mapped_column(ForeignKey("media_item.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class LibraryFile(Base):
    __tablename__ = "library_file"
    __table_args__ = (UniqueConstraint("episode_id", "path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episode.id"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sha1: Mapped[str | None] = mapped_column(String)
    quality_bucket: Mapped[str] = mapped_column(String, default="sd", nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32))
    landed_verified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class StrmRecord(Base):
    __tablename__ = "strm_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    library_file_id: Mapped[int] = mapped_column(
        ForeignKey("library_file.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strm_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Account(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, default="", nullable=False)
    credential: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transfer_path: Mapped[str] = mapped_column(String, default="/CSX/_inbox", nullable=False)
    media_path: Mapped[str] = mapped_column(String, default="/CSX/媒体库", nullable=False)
    quota_state: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Setting(Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class CheckinRecord(Base):
    """Persistent result of one drive account check-in attempt."""

    __tablename__ = "checkin_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("account.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    account_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    reward: Mapped[str] = mapped_column(Text, default="", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    consecutive_days: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
