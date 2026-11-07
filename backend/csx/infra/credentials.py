"""Encryption helpers for stored drive credentials."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from csx.infra.settings import settings


def _fernet() -> Fernet:
    if not settings.secret_key:
        raise RuntimeError("CSX_SECRET_KEY must be configured to store drive credentials")
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt_credential(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_credential(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
