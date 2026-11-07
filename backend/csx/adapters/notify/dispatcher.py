"""Best-effort concurrent notification fan-out."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .feishu import FeishuNotifier
from .telegram import TelegramNotifier
from .webhook import WebhookNotifier


class NotificationDispatcher:
    def __init__(self, senders: Mapping[str, Any] | None = None, *, max_workers: int = 4) -> None:
        self.senders = dict(
            senders
            or {
                "webhook": WebhookNotifier(),
                "telegram": TelegramNotifier(),
                "feishu": FeishuNotifier(),
            }
        )
        self.max_workers = max(1, max_workers)

    def close(self) -> None:
        for sender in self.senders.values():
            close = getattr(sender, "close", None)
            if callable(close):
                close()

    def dispatch(
        self, settings: Mapping[str, Any], event: str, payload: Mapping[str, Any]
    ) -> dict[str, str]:
        """Send to enabled configured channels; individual failures never escape."""
        configured = settings.get("channels", settings)
        jobs: list[tuple[str, Any, Mapping[str, Any]]] = []
        for name, sender in self.senders.items():
            item = configured.get(name) if isinstance(configured, Mapping) else None
            if not isinstance(item, Mapping) or not item.get("enabled", False):
                continue
            jobs.append((name, sender, item))
        results: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(sender.send, event, payload, config): name
                for name, sender, config in jobs
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    future.result()
                    results[name] = "sent"
                except Exception as error:
                    results[name] = f"failed: {error}"
        return results
