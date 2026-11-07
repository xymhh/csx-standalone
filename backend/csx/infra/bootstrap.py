"""首次启动时创建管理员账号。"""

from __future__ import annotations

import logging
import secrets
from asyncio import Task
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from csx.infra.db import SessionLocal, engine
from csx.infra.events import event_bus
from csx.infra.migrations import upgrade_to_head
from csx.infra.models import AdminUser, TransferTask
from csx.infra.security import hash_password
from csx.infra.settings import settings

logger = logging.getLogger(__name__)
_recovery_event_tasks: set[Task] = set()


def init_db() -> None:
    upgrade_to_head(engine)
    recover_stale_tasks()


def recover_stale_tasks(session_factory: sessionmaker = SessionLocal) -> dict[str, int]:
    """Requeue interrupted work on startup and dead-letter exhausted tasks."""
    now = datetime.now(UTC).replace(tzinfo=None)
    with session_factory() as db:
        retry_result = db.execute(
            update(TransferTask)
            .where(TransferTask.state == "running", TransferTask.attempt < 3)
            .values(
                state="retry_wait",
                next_retry_at=now,
                last_error="PROCESS_CRASHED_ORPHAN",
                updated_at=now,
            )
        )
        dead_result = db.execute(
            update(TransferTask)
            .where(TransferTask.state == "running", TransferTask.attempt >= 3)
            .values(
                state="dead_letter",
                dead_letter=1,
                last_error="PROCESS_CRASHED_ORPHAN",
                updated_at=now,
            )
        )
        db.commit()
        counts = {"retry_wait": retry_result.rowcount, "dead_letter": dead_result.rowcount}

    total = counts["retry_wait"] + counts["dead_letter"]
    if total:
        logger.warning(
            "启动恢复处理了 %d 个运行中孤儿任务（重试 %d，死信 %d）",
            total,
            counts["retry_wait"],
            counts["dead_letter"],
        )
        try:
            import asyncio

            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            task = loop.create_task(event_bus.publish("system_recovery", counts))
            _recovery_event_tasks.add(task)
            task.add_done_callback(_recovery_event_tasks.discard)
    return counts


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
