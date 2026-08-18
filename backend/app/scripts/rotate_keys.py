"""Rotate the Fernet encryption key used for provider/storage secrets.

Procedure:
    1. Back up your database.
    2. Set ENCRYPTION_KEY to the NEW key and ENCRYPTION_KEYS to the comma-separated
       OLD key(s) (so existing secrets can still be decrypted).
    3. Run: python -m app.scripts.rotate_keys
    4. The script re-encrypts every secret with the new key.
    5. Remove ENCRYPTION_KEYS (or keep it empty) and restart the backend.

Example:
    ENCRYPTION_KEY="new-key-at-least-32-bytes-long" \\
    ENCRYPTION_KEYS="old-key-at-least-32-bytes" \\
    python -m app.scripts.rotate_keys
"""

from __future__ import annotations

import json

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal, init_db
from app.core.encryption import decrypt_secret, encrypt_secret
from app.models import Provider, StorageBackend

settings = get_settings()


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        providers = list(db.scalars(select(Provider)))
        backends = list(db.scalars(select(StorageBackend)))
        total = len(providers) + len(backends)

        if settings.encryption_keys:
            print(f"Rotation with legacy keys: {settings.encryption_keys}")
        print(f"Re-encrypting {total} secret(s) with the new ENCRYPTION_KEY...")

        changed = 0
        for p in providers:
            if p.api_key_encrypted:
                plain = decrypt_secret(p.api_key_encrypted)
                p.api_key_encrypted = encrypt_secret(plain)
                changed += 1
        for b in backends:
            if b.config_encrypted:
                plain = decrypt_secret(b.config_encrypted)
                b.config_encrypted = encrypt_secret(plain)
                changed += 1
        db.commit()
        print(f"Done: {changed} secret(s) re-encrypted.")
        if changed != total:
            print("Note: some secrets were empty and skipped.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
