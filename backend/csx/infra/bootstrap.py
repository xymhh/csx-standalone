"""首次启动时创建管理员账号。"""

from __future__ import annotations

import logging
import secrets

from sqlalchemy import select

from csx.infra.db import SessionLocal, engine
from csx.infra.migrations import upgrade_to_head
from csx.infra.models import AdminUser
from csx.infra.security import hash_password
from csx.infra.settings import settings

logger = logging.getLogger(__name__)


def init_db() -> None:
    upgrade_to_head(engine)


def ensure_admin() -> None:
    with SessionLocal() as db:
        if db.scalar(select(AdminUser).limit(1)) is not None:
            return

        username = settings.admin_user
        password = settings.admin_password or secrets.token_urlsafe(12)
        db.add(AdminUser(username=username, password_hash=hash_password(password)))
        db.commit()

        if settings.admin_password:
            logger.info("已创建管理员账号 %s（密码来自 CSX_ADMIN_PASSWORD）", username)
        else:
            path = settings.data_dir / "initial-admin-password.txt"
            path.write_text(f"{username}\n{password}\n")
            path.chmod(0o600)
            logger.warning("已创建管理员账号 %s，初始密码写入 %s", username, path)
