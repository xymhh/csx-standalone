"""Telegram Bot API notification transport."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx


class TelegramNotifier:
    def __init__(self, client: httpx.Client | None = None, *, timeout: float = 10.0) -> None:
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout)

    def send(self, event: str, payload: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        token = str(config.get("bot_token") or config.get("token") or "").strip()
        chat_id = str(config.get("chat_id") or "").strip()
        if not token or not chat_id:
            raise ValueError("Telegram bot_token/chat_id 未配置")
        lines = [f"*{event}*"]
        lines.extend(f"{key}: {value}" for key, value in payload.items())
        response = self.client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": "\n".join(lines), "parse_mode": "Markdown"},
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and result.get("ok") is False:
            raise RuntimeError(str(result.get("description") or "Telegram 发送失败"))

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
