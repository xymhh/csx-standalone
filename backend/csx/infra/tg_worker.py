"""Background loop that periodically scans configured Telegram channels."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable, Mapping
from typing import Any

from csx.application.tg_sync import is_configured, load_tg_config, run_scan
from csx.infra.db import SessionLocal
from csx.infra.tg_client import client_from_config
from csx.infra.tg_errors import TgAuthError, TgNotConfigured

logger = logging.getLogger(__name__)


class TgWorker:
    """Single asyncio task; failures never terminate the loop."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Any] = SessionLocal,
        client_factory: Callable[[Mapping[str, Any]], Any] = client_from_config,
        start_delay: float = 20.0,
        disabled_poll_seconds: float = 60.0,
        channel_sleep: float = 1.5,
        scan_limit: int = 50,
    ) -> None:
        self.session_factory = session_factory
        self.client_factory = client_factory
        self.start_delay = start_delay
        self.disabled_poll_seconds = disabled_poll_seconds
        self.channel_sleep = channel_sleep
        self.scan_limit = scan_limit
        self.last_error: str | None = None
        self._task: asyncio.Task | None = None
        self._stopping = False

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._stopping = False
        self._task = asyncio.create_task(self._loop(), name="csx-tg-worker")

    async def stop(self) -> None:
        self._stopping = True
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def scan_once(self) -> dict[str, Any]:
        return await run_scan(
            self.session_factory,
            self.client_factory,
            limit=self.scan_limit,
            channel_sleep=self.channel_sleep,
        )

    def _config(self) -> dict[str, Any]:
        with self.session_factory() as session:
            return load_tg_config(session)

    async def _loop(self) -> None:
        try:
            await asyncio.sleep(self.start_delay)
            while not self._stopping:
                try:
                    config = self._config()
                except Exception as error:
                    self.last_error = f"读取 TG 设置失败（{type(error).__name__}）"
                    await asyncio.sleep(self.disabled_poll_seconds)
                    continue

                if not config.get("enabled") or not is_configured(config):
                    self.last_error = None
                    await asyncio.sleep(self.disabled_poll_seconds)
                    continue

                try:
                    result = await self.scan_once()
                    errors = result.get("errors") or []
                    self.last_error = str(errors[0]) if errors else None
                    logger.info(
                        "TG 扫描完成：频道 %s，新消息 %s，入库 %s",
                        result.get("scanned_channels"),
                        result.get("new_messages"),
                        result.get("ingested"),
                    )
                except TgNotConfigured:
                    self.last_error = None
                except TgAuthError as error:
                    self.last_error = str(error)
                    logger.warning("TG 会话失效，等待重新导出 StringSession")
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    self.last_error = f"TG 扫描失败（{type(error).__name__}）"
                    logger.warning("TG 扫描失败：%s", type(error).__name__)

                await asyncio.sleep(max(1, int(config["interval_minutes"])) * 60)
        except asyncio.CancelledError:
            return
