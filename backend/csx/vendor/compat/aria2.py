"""Compatibility fallback for the optional MoviePilot aria2 acceleration module."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def aria2_settings() -> SimpleNamespace:
    """Disable the optional host-managed aria2 path in the standalone vendor."""
    return SimpleNamespace(enabled=False)


class Aria2FileDownloadService:
    """Explicit failure if the disabled optional acceleration path is forced on."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise NotImplementedError("MoviePilot aria2 acceleration is unavailable in standalone mode")
