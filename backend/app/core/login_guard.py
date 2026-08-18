from __future__ import annotations

import hashlib

from fastapi import HTTPException

from app.core import redis as redis_store
from app.core.config import get_settings

settings = get_settings()


def _key(*parts: str) -> str:
    digest = hashlib.sha1(":".join(parts).encode()).hexdigest()[:24]
    return f"authguard:{digest}"


def check_login_allowed(ip: str, email: str) -> None:
    """Reject requests that are rate-limited or lockout-blocked (brute force guard)."""
    rl_key = _key("rl", ip)
    count = int(redis_store._client.get(rl_key) or 0)
    if count >= settings.login_rate_limit:
        raise HTTPException(429, "Trop de tentatives de connexion, réessayez plus tard")

    lock_key = _key("lock", ip, email.lower())
    remaining = redis_store._client.ttl(lock_key)
    if int(redis_store._client.get(lock_key) or 0) >= settings.login_max_failures:
        raise HTTPException(423, f"Compte temporairement verrouillé, réessayez dans {max(remaining, 0)}s")

    redis_store._client.incr(rl_key)
    redis_store._client.expire(rl_key, settings.login_rate_window_seconds)


def record_login_failure(ip: str, email: str) -> None:
    lock_key = _key("lock", ip, email.lower())
    current = int(redis_store._client.incr(lock_key))
    if current >= settings.login_max_failures:
        redis_store._client.expire(lock_key, settings.login_lockout_seconds)
    else:
        redis_store._client.expire(lock_key, settings.login_rate_window_seconds)


def reset_login_failures(ip: str, email: str) -> None:
    lock_key = _key("lock", ip, email.lower())
    redis_store._client.delete(lock_key)
