from __future__ import annotations

import time

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core import redis as redis_store

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limit per (client, path prefix)."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/api/v1/health", "/docs", "/openapi.json"):
            return await call_next(request)

        key = self._key(request)
        count = int(redis_store._client.get(key) or 0)
        if count >= settings.rate_limit_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        redis_store._client.incr(key)
        redis_store._client.expire(key, settings.rate_limit_window_seconds)
        return await call_next(request)

    @staticmethod
    def _key(request: Request) -> str:
        ip = request.client.host if request.client else "unknown"
        user = None
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            from app.core.security import decode_token
            try:
                user = decode_token(auth.split(" ", 1)[1]).get("sub")
            except Exception:
                pass
        return f"rl:{ip}:{user or 'anon'}:{request.url.path.split('/')[3] if len(request.url.path.split('/')) > 3 else 'root'}"
