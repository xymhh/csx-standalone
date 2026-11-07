"""Runtime access to configured DrivePort adapters."""

from __future__ import annotations

from sqlalchemy.orm import Session

from csx.adapters.drive.registry import DriveRegistry
from csx.infra.credentials import decrypt_credential
from csx.infra.models import Account


def configured_drives(db: Session) -> dict[str, object]:
    return DriveRegistry.from_session(db)


def drive_for(db: Session, provider: str, configured: dict[str, object] | None = None):
    drives = configured or {}
    if provider in drives:
        return drives[provider]
    account = db.query(Account).filter(Account.provider == provider).first()
    if account is None:
        return None
    credential = decrypt_credential(account.credential)
    return DriveRegistry.build(provider, credential)
