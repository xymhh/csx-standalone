"""Telethon-backed Telegram user client.

All Telethon imports live here so the application layer never depends on it.
Credentials and session strings are never written to logs.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping
from typing import Any

from telethon import TelegramClient
from telethon.errors import (
    AuthKeyDuplicatedError,
    AuthKeyUnregisteredError,
    ChannelInvalidError,
    ChannelPrivateError,
    ChatAdminRequiredError,
    FloodWaitError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    PhoneNumberBannedError,
    SessionRevokedError,
    UserDeactivatedBanError,
    UserDeactivatedError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.sessions import StringSession

from csx.infra.tg_errors import (
    TgAuthError,
    TgChannelError,
    TgError,
    TgFloodWait,
    TgNotConfigured,
)

__all__ = [
    "TgAuthError",
    "TgChannelError",
    "TgClient",
    "TgError",
    "TgFloodWait",
    "TgNotConfigured",
    "client_from_config",
]

_AUTH_ERRORS = (
    AuthKeyDuplicatedError,
    AuthKeyUnregisteredError,
    PhoneNumberBannedError,
    SessionRevokedError,
    UserDeactivatedBanError,
    UserDeactivatedError,
)
_CHANNEL_ERRORS = (
    ChannelInvalidError,
    ChannelPrivateError,
    ChatAdminRequiredError,
    InviteHashExpiredError,
    InviteHashInvalidError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)


def _mapped_error(error: Exception) -> Exception | None:
    if isinstance(error, FloodWaitError):
        return TgFloodWait(int(getattr(error, "seconds", 0) or 0))
    if isinstance(error, _AUTH_ERRORS):
        return TgAuthError("TG 会话已失效，请重新导出 StringSession")
    if isinstance(error, _CHANNEL_ERRORS):
        return TgChannelError(f"频道不可访问（{type(error).__name__}）")
    return None


class TgClient:
    """Small async wrapper around one Telethon client instance."""

    def __init__(self, api_id: Any, api_hash: Any, session: Any, *, timeout: int = 20) -> None:
        self.api_id = str(api_id or "").strip()
        self.api_hash = str(api_hash or "").strip()
        self.session = str(session or "").strip()
        self.timeout = timeout
        self._client: TelegramClient | None = None

    @property
    def configured(self) -> bool:
        return bool(self.api_id and self.api_hash and self.session)

    async def connect(self) -> None:
        if not self.configured:
            raise TgNotConfigured("请先配置 Telegram API ID、API Hash 与 StringSession")
        if self._client is not None:
            return
        client = TelegramClient(
            StringSession(self.session),
            int(self.api_id),
            self.api_hash,
            timeout=self.timeout,
            connection_retries=3,
        )
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise TgAuthError("TG 会话已失效，请重新导出 StringSession")
        except Exception as error:
            with contextlib.suppress(Exception):
                await client.disconnect()
            mapped = _mapped_error(error)
            if mapped is not None:
                raise mapped from error
            if isinstance(error, TgError):
                raise
            raise TgError(f"TG 连接失败（{type(error).__name__}）") from error
        self._client = client

    async def close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            with contextlib.suppress(Exception):
                await client.disconnect()

    async def fetch(self, channel: str, min_id: int, limit: int) -> list[dict[str, Any]]:
        """Return text messages newer than ``min_id`` in ascending id order."""
        client = self._client
        if client is None:
            raise TgError("TG 客户端尚未连接")
        try:
            entity = await client.get_entity(channel)
            if min_id > 0:
                raw_messages = await client.get_messages(
                    entity, min_id=min_id, limit=limit, reverse=True
                )
            else:
                raw_messages = await client.get_messages(entity, limit=limit)
                raw_messages = list(reversed(list(raw_messages or [])))
        except Exception as error:
            mapped = _mapped_error(error)
            if mapped is not None:
                raise mapped from error
            if isinstance(error, TgError):
                raise
            raise TgChannelError(f"读取频道失败（{type(error).__name__}）") from error

        messages: list[dict[str, Any]] = []
        for message in raw_messages or []:
            text = str(getattr(message, "text", None) or getattr(message, "message", "") or "")
            text = text.strip()
            if not text:
                continue
            message_id = int(getattr(message, "id", 0) or 0)
            if message_id <= min_id:
                continue
            messages.append(
                {
                    "id": message_id,
                    "text": text,
                    "date": getattr(message, "date", None),
                }
            )
        messages.sort(key=lambda item: int(item["id"]))
        return messages


def client_from_config(config: Mapping[str, Any]) -> TgClient:
    return TgClient(
        config.get("api_id"),
        config.get("api_hash"),
        config.get("session"),
    )
