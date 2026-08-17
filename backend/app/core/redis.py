from __future__ import annotations

import json
import time
from typing import Optional

from app.core.config import get_settings

_settings = get_settings()

_USE_FAKE = True


def _connect() -> object:
    """Return a redis client. Uses fakeredis when real redis is unavailable."""
    try:
        import redis

        client = redis.Redis.from_url(_settings.redis_url, socket_connect_timeout=2)
        client.ping()
        return client
    except Exception:
        import fakeredis

        return fakeredis.FakeStrictRedis(decode_responses=True)


_client: object = _connect()


def get_redis():
    return _client


def set_json(key: str, value, ttl: Optional[int] = None) -> None:
    _client.set(key, json.dumps(value), ex=ttl)


def get_json(key: str):
    raw = _client.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return raw


def delete_key(key: str) -> None:
    _client.delete(key)


def acquire_lock(name: str, ttl_seconds: int = 60) -> bool:
    try:
        return bool(_client.set(f"lock:{name}", "1", nx=True, ex=ttl_seconds))
    except Exception:
        return True


def release_lock(name: str) -> None:
    try:
        _client.delete(f"lock:{name}")
    except Exception:
        pass


def enqueue(queue: str, payload: dict) -> None:
    _client.rpush(f"queue:{queue}", json.dumps(payload))


def dequeue(queue: str, timeout_seconds: int = 2):
    item = _client.blpop(f"queue:{queue}", timeout=timeout_seconds)
    if item is None:
        return None
    _, raw = item
    return json.loads(raw)
