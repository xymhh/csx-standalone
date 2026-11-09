"""Generic JSON webhook notification transport."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx


class WebhookNotifier:
    def __init__(self, client: httpx.Client | None = None, *, timeout: float = 10.0) -> None:
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout)

    def send(self, event: str, payload: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        url = str(config.get("url") or config.get("webhook_url") or "").strip()
        if not url:
            raise ValueError("Webhook URL 未配置")
        data = {key: value for key, value in payload.items() if key != "text"}
        response = self.client.post(
            url,
            json={"event": event, "text": str(payload.get("text") or ""), "data": data},
        )
        response.raise_for_status()

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
