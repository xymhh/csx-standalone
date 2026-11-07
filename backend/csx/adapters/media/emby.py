"""Emby/Jellyfin connectivity probe and library refresh client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ServerInfo:
    provider: str
    name: str
    version: str
    raw: dict[str, Any]


class EmbyClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        provider: str = "emby",
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.provider = provider.lower()
        self.client = client or httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {"X-Emby-Token": self.api_key, "X-MediaBrowser-Token": self.api_key}

    def probe(self) -> ServerInfo:
        if not self.base_url:
            raise ValueError("媒体服务器 URL 未配置")
        response = self.client.get(
            f"{self.base_url}/System/Info",
            params={"api_key": self.api_key} if self.api_key else None,
            headers=self._headers(),
        )
        response.raise_for_status()
        data = response.json()
        return ServerInfo(
            provider=self.provider,
            name=str(data.get("ServerName") or data.get("Name") or self.provider),
            version=str(data.get("Version") or ""),
            raw=data,
        )

    def refresh(self, library_id: str | None = None) -> None:
        if not self.base_url:
            raise ValueError("媒体服务器 URL 未配置")
        params: dict[str, str] = {"api_key": self.api_key} if self.api_key else {}
        if library_id:
            params["LibraryId"] = library_id
        response = self.client.post(
            f"{self.base_url}/Library/Refresh",
            params=params or None,
            headers=self._headers(),
        )
        response.raise_for_status()

    def close(self) -> None:
        self.client.close()


# Keep a descriptive alias for call sites that distinguish server brand.
MediaServerClient = EmbyClient


def server_clients(settings: dict[str, Any], *, client_factory=None) -> list[EmbyClient]:
    """Construct configured clients from a flat settings mapping."""
    factory = client_factory or EmbyClient
    result = []
    for provider in ("emby", "jellyfin"):
        base_url = str(settings.get(f"{provider}_url") or "").strip()
        api_key = str(settings.get(f"{provider}_api_key") or "").strip()
        if base_url:
            result.append(factory(base_url, api_key, provider=provider))
    return result
