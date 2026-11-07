"""登录、会话、改密的用例。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from csx.infra.models import AdminUser, AuthSession
from csx.infra.security import (
    hash_password,
    new_session_token,
    token_fingerprint,
    verify_password,
)
from csx.infra.settings import settings


def authenticate(db: Session, username: str, password: str) -> AdminUser | None:
    user = db.scalar(select(AdminUser).where(AdminUser.username == username))
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, user: AdminUser, ip: str, user_agent: str) -> str:
    token = new_session_token()
    db.add(
        AuthSession(
            token_hash=token_fingerprint(token),
            user_id=user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            + timedelta(days=settings.session_ttl_days),
            ip=ip[:64],
            user_agent=user_agent[:255],
        )
    )
    db.commit()
    return token


def session_user(db: Session, token: str) -> AdminUser | None:
    if not token:
        return None
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_fingerprint(token)))
    if row is None:
        return None
    if row.expires_at < datetime.now(UTC).replace(tzinfo=None):
        db.execute(delete(AuthSession).where(AuthSession.id == row.id))
        db.commit()
        return None
    return db.get(AdminUser, row.user_id)


def revoke_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token_hash == token_fingerprint(token)))
    db.commit()


def change_password(db: Session, user: AdminUser, old: str, new: str) -> bool:
    if not verify_password(old, user.password_hash):
        return False
    user.password_hash = hash_password(new)
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.commit()
    return True
