"""Best-effort P6 notifications and post-transfer library side effects."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from csx.adapters.db.strm import SqlAlchemyStrmRepository
from csx.adapters.drive.registry import DriveRegistry
from csx.adapters.media.emby import server_clients
from csx.adapters.notify import NotificationDispatcher
from csx.application.strm import StrmService
from csx.infra.models import Setting

logger = logging.getLogger(__name__)


def section_settings(db, section: str) -> dict[str, Any]:
    rows = db.scalars(select(Setting).where(Setting.key.like(f"{section}.%")))
    return {row.key.split(".", 1)[1]: json.loads(row.value) for row in rows}


def dispatch_notification(
    config: Mapping[str, Any], event: str, payload: Mapping[str, Any]
) -> None:
    dispatcher = NotificationDispatcher()
    try:
        dispatcher.dispatch(config, event, payload)
    except Exception:
        logger.exception("notification dispatch failed: %s", event)
    finally:
        dispatcher.close()


def dispatch_notification_later(
    config: Mapping[str, Any], event: str, payload: Mapping[str, Any]
) -> None:
    threading.Thread(
        target=dispatch_notification,
        args=(dict(config), event, dict(payload)),
        name=f"csx-notify-{event}",
        daemon=True,
    ).start()


def post_transfer_side_effects(
    session_factory, result: Mapping[str, Any], resource: Mapping[str, Any]
) -> None:
    """Run STRM refresh and notification after the transfer transaction committed."""
    try:
        with session_factory() as db:
            config = section_settings(db, "strm")
            if result.get("ok") and config.get("strm_root"):
                direct_mode = str(config.get("mode") or "local_mount").lower() == "direct"
                drives = DriveRegistry.from_session(db) if direct_mode else {}
                sync = StrmService(
                    SqlAlchemyStrmRepository(db), strm_settings=config, drives=drives
                ).sync()
                db.commit()
                if sync.errors:
                    logger.warning("post-transfer STRM errors: %s", sync.errors)
            notify_config = section_settings(db, "notify")
            advanced = section_settings(db, "advanced")
        if result.get("ok"):
            event = "upgrade_success" if result.get("is_upgrade") else "transfer_success"
            media = resource.get("media") if isinstance(resource.get("media"), dict) else {}
            payload = {
                "title": media.get("title", ""),
                "season": result.get("season", resource.get("season", "")),
                "episode": result.get("episode", resource.get("episode", "")),
                "quality": result.get("quality_bucket", resource.get("quality_bucket", "")),
                "duration": result.get("duration", ""),
                "from_quality": result.get("existing_bucket", ""),
                "to_quality": result.get("quality_bucket", resource.get("quality_bucket", "")),
            }
            dispatch_notification_later(notify_config, event, payload)
            for client in server_clients(advanced):
                try:
                    client.refresh()
                except Exception:
                    logger.exception("media library refresh failed for %s", client.provider)
                finally:
                    client.close()
        elif result.get("state") == "dead_letter":
            dispatch_notification_later(
                notify_config,
                "task_dead_letter",
                {
                    "error": result.get("error", ""),
                    "share_url": resource.get("share_url", ""),
                },
            )
    except Exception:
        logger.exception("post-transfer side effects failed")


def schedule_transfer_side_effects(
    session_factory, result: Mapping[str, Any], resource: Mapping[str, Any]
) -> None:
    threading.Thread(
        target=post_transfer_side_effects,
        args=(session_factory, dict(result), dict(resource)),
        name="csx-post-transfer",
        daemon=True,
    ).start()
