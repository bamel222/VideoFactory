from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
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
    from app import models  # noqa: F401  ensure models registered

    Base.metadata.create_all(bind=engine)
    _light_migrations(engine)


_SQLITE_ADD_COLUMNS = {
    "series": [
        ("generation_mode", "VARCHAR(20) DEFAULT ''"),
        ("duration_minutes", "INTEGER DEFAULT 26"),
        ("fact_check_enabled", "BOOLEAN DEFAULT 1"),
    ],
}


def _light_migrations(engine_) -> None:
    """Additive, idempotent column migrations for SQLite dev databases."""
    if not str(engine_.url).startswith("sqlite"):
        return
    with engine_.begin() as conn:
        for table, columns in _SQLITE_ADD_COLUMNS.items():
            if not inspect(conn).has_table(table):
                continue
            existing = {c["name"] for c in inspect(conn).get_columns(table)}
            for name, ddl in columns:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
