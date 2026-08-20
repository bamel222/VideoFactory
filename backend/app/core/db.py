from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_url = _settings.database_url

_engine_kwargs: dict = {"echo": False}
if _url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["pool_pre_ping"] = True
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Bring the database schema up to date using Alembic migrations.

    Replaces the old `create_all` + ad-hoc SQLite column migrations. Legacy dev
    databases created before Alembic are adopted by stamping them at head (their
    existing tables are kept and future migrations apply cleanly on top).
    """
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    import app.models  # noqa: F401  ensure models are registered on Base.metadata

    # This file lives at backend/app/core/db.py; the Alembic project root is backend/.
    here = str(Path(__file__).resolve().parents[2])
    cfg = Config(os.path.join(here, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "alembic"))

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if tables and "alembic_version" not in tables:
        # Pre-Alembic database: adopt the existing schema (which matches the
        # base migration) by stamping it at the base revision, then apply any
        # additive migrations on top (so new columns are added, not skipped).
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(cfg)
        base_rev = script.get_base()
        command.stamp(cfg, base_rev.revision)
        command.upgrade(cfg, "head")
    else:
        command.upgrade(cfg, "head")
