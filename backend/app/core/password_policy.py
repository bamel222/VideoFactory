from __future__ import annotations

import datetime as dt
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_password
from app.models import PasswordHistory, User

settings = get_settings()


def validate_password_strength(password: str) -> list[str]:
    """Return a list of human-readable violations for a password.

    An empty list means the password satisfies the configured policy.
    """
    violations: list[str] = []
    if len(password) < settings.password_min_length:
        violations.append(f"Au moins {settings.password_min_length} caractères requis")
    if settings.password_require_upper and not re.search(r"[A-Z]", password):
        violations.append("Au moins une lettre majuscule requise")
    if settings.password_require_lower and not re.search(r"[a-z]", password):
        violations.append("Au moins une lettre minuscule requise")
    if settings.password_require_digit and not re.search(r"\d", password):
        violations.append("Au moins un chiffre requis")
    if settings.password_require_symbol and not re.search(r"[^A-Za-z0-9]", password):
        violations.append("Au moins un caractère spécial requis")
    return violations


def enforce_password_policy(password: str) -> None:
    from fastapi import HTTPException

    violations = validate_password_strength(password)
    if violations:
        raise HTTPException(400, {"code": "WEAK_PASSWORD", "message": "Mot de passe trop faible", "violations": violations})


def password_is_reused(db: Session, user: User, plaintext: str) -> bool:
    """True if the plaintext matches any of the user's last N password hashes."""
    history = list(
        db.scalars(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user.id)
            .order_by(PasswordHistory.id.desc())
            .limit(settings.password_history_size)
        )
    )
    return any(verify_password(plaintext, h.hashed_password) for h in history)


def record_password(db: Session, user: User, new_hashed: str) -> None:
    """Store the new hash in history (trimmed) and stamp password_changed_at."""
    db.add(PasswordHistory(user_id=user.id, hashed_password=new_hashed))
    old = list(
        db.scalars(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user.id)
            .order_by(PasswordHistory.id.asc())
        )
    )
    overflow = len(old) - settings.password_history_size
    for h in old[: max(overflow, 0)]:
        db.delete(h)
    user.password_changed_at = dt.datetime.now(dt.timezone.utc)


def password_expired(user: User) -> bool:
    """True when the password must be rotated (per max age policy)."""
    if not settings.password_max_age_days:
        return False
    if not user.password_changed_at:
        return True
    age = dt.datetime.now(dt.timezone.utc) - _as_utc(user.password_changed_at)
    return age.days >= settings.password_max_age_days


def _as_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value
