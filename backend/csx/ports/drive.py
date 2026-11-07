"""Drive provider port and transport result types."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ShareStatus:
    valid: bool
    error: str = ""
    password_required: bool = False


@dataclass(frozen=True)
class ShareFile:
    file_id: str
    name: str
    size: int = 0
    sha1: str = ""
    path: str = ""


@dataclass(frozen=True)
class CloudFile:
    file_id: str
    name: str
    path: str
    size: int = 0
    sha1: str = ""


@dataclass(frozen=True)
class TransferOutcome:
    ok: bool
    failed_files: list[str] = field(default_factory=list)
    created: list[tuple[str, str, int, str]] = field(default_factory=list)
    error: str = ""


class DrivePort(Protocol):
    provider: str

    def check_share(self, share_url: str, password: str = "") -> ShareStatus: ...

    def list_share_files(self, share_url: str, password: str = "") -> list[ShareFile]: ...

    def transfer(
        self,
        share_url: str,
        target_dir: str,
        *,
        file_ids: Sequence[str],
        password: str = "",
        rename_map: Mapping[str, str] | None = None,
    ) -> TransferOutcome: ...

    def move(self, file_id: str, target_dir: str) -> None: ...

    def rename(self, file_id: str, new_name: str) -> None: ...

    def list_dir(self, path: str) -> list[CloudFile]: ...
