from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _derive_key(secret: str) -> bytes:
    if len(secret.encode()) < 16:
        raise ValueError("ENCRYPTION_KEY must be at least 16 bytes")
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _build_fernets() -> list[Fernet]:
    settings = get_settings()
    keys: list[str] = [settings.encryption_key]
    if settings.encryption_keys:
        keys += [k.strip() for k in settings.encryption_keys.split(",") if k.strip()]
    return [Fernet(_derive_key(k)) for k in keys]


# First entry is the primary (encryption) key; the rest are legacy keys for decryption.
_FERNETS = _build_fernets()


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _FERNETS[0].encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    for fernet in _FERNETS:
        try:
            return fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            continue
    return ""


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    return value[:2] + "*" * (len(value) - 4) + value[-2:]
