from __future__ import annotations

import datetime as dt
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

ROLE_ORDER = {"owner": 3, "admin": 2, "reviewer": 1}
ROLES = ("owner", "admin", "reviewer")

# Action matrix: role -> allowed actions
PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        "billing.manage", "secrets.manage", "providers.delete", "users.manage",
        "users.delete", "publication.final", "roles.manage", "workspace.delete",
        "providers.manage", "storage.manage", "jobs.manage", "review.operational",
        "seo.manage", "audit.read", "series.manage", "pipeline.run",
    },
    "admin": {
        "providers.manage_noncritical", "storage.manage", "jobs.manage",
        "review.operational", "seo.manage", "series.manage", "pipeline.run",
        "audit.read",
    },
    "reviewer": {
        "review.quality", "review.read", "content.read",
    },
}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: int, email: str, role: str, workspace_id: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "workspace_id": workspace_id,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def role_has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def require_permission(role: str, permission: str) -> bool:
    return role_has_permission(role, permission)
