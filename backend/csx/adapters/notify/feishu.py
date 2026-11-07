"""Feishu group bot rich-card notification transport."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx


class FeishuNotifier:
    def __init__(self, client: httpx.Client | None = None, *, timeout: float = 10.0) -> None:
        self._owns_client = client is None
        self.client = client or httpx.Client(timeout=timeout)

    def send(self, event: str, payload: Mapping[str, Any], config: Mapping[str, Any]) -> None:
        url = str(config.get("webhook_url") or config.get("url") or "").strip()
        if not url:
            raise ValueError("飞书 webhook_url 未配置")
        body = "\n".join(f"**{key}**: {value}" for key, value in payload.items())
        response = self.client.post(
            url,
            json={
                "msg_type": "interactive",
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": event}},
                    "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": body}}],
                },
            },
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and int(result.get("code", 0)) != 0:
            raise RuntimeError(str(result.get("msg") or "飞书发送失败"))

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
