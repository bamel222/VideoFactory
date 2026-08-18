from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import init_db
from app.core.middleware import SecurityHeadersMiddleware
from app.core.observability import RequestLoggingMiddleware
from app.core.ratelimit import RateLimitMiddleware

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
# Credentials (cookies/authorization) are only forwarded to explicit origins.
# A wildcard "*" origin forces allow_credentials=False (browsers reject wildcard+credentials anyway).
_allow_credentials = settings.cors_allow_credentials and "*" not in settings.cors_origins_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Bootstrap-Token", "Content-Disposition"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)


@app.on_event("startup")
def on_startup() -> None:
    os.makedirs(settings.data_dir, exist_ok=True)
    os.makedirs(os.path.join(settings.data_dir, "storage"), exist_ok=True)
    os.makedirs(os.path.join(settings.data_dir, "media"), exist_ok=True)
    init_db()


@app.get("/health", tags=["system"])
def health():
    from sqlalchemy import text

    from app.core.db import SessionLocal

    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_ok = False
    return {
        "status": "ok",
        "app": settings.app_name,
        "db": "ok" if db_ok else "error",
        "redis": "ok",
    }


@app.get("/", tags=["system"])
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/health"}


# Routers
from app.api import audit, auth, jobs, monetization, providers, publishing, review, seo, series, settings as settings_api, storage, users  # noqa: E402

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(storage.router, prefix="/api/v1")
app.include_router(series.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(publishing.router, prefix="/api/v1")
app.include_router(seo.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(settings_api.router, prefix="/api/v1")
app.include_router(monetization.router, prefix="/api/v1")
