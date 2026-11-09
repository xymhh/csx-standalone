"""Telethon-independent error types shared by the Telegram client and sync layer."""

from __future__ import annotations


class TgError(Exception):
    """Base class for Telegram client failures."""


class TgNotConfigured(TgError):
    """API id, API hash or StringSession is missing."""


class TgAuthError(TgError):
    """The saved Telegram user session is no longer valid."""


class TgFloodWait(TgError):
    """Telegram asked us to wait before sending more requests."""

    def __init__(self, seconds: int, message: str | None = None) -> None:
        self.seconds = max(0, int(seconds))
        super().__init__(message or f"Telegram 限流，需要等待 {self.seconds} 秒")


class TgChannelError(TgError):
    """A single channel cannot be resolved or read."""
