from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

PROVIDER_ROLES = (
    "research", "transcription", "translation", "script", "tts", "voice", "music",
    "image", "video", "assembly", "seo", "qa", "licensing", "caption",
)


class Provider(Base, TimestampMixin):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), default="")
    api_key_encrypted: Mapped[str] = mapped_column(String(1000), default="")
    quota_total: Mapped[int] = mapped_column(Integer, default=0)
    quota_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_per_unit: Mapped[float] = mapped_column(Float, default=0.0)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|disabled|paused
    languages: Mapped[list] = mapped_column(JSON, default=list)
    formats: Mapped[list] = mapped_column(JSON, default=list)
    limits: Mapped[dict] = mapped_column(JSON, default=dict)
    model: Mapped[str] = mapped_column(String(255), default="")
    avg_speed: Mapped[str] = mapped_column(String(50), default="")
    quality_estimate: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    last_healthcheck_at: Mapped[str] = mapped_column(String(50), default="")
    healthy: Mapped[bool] = mapped_column(default=True, nullable=False)


STORAGE_KINDS = ("local", "pcloud", "supabase", "s3", "r2", "b2", "minio", "nas")


class StorageBackend(Base, TimestampMixin):
    __tablename__ = "storage_backends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    config_encrypted: Mapped[str] = mapped_column(String(2000), default="")  # JSON payload
    priority: Mapped[int] = mapped_column(Integer, default=100)
    quota_bytes: Mapped[int] = mapped_column(Integer, default=0)
    used_bytes: Mapped[int] = mapped_column(Integer, default=0)
    cost_per_gb: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    region: Mapped[str] = mapped_column(String(50), default="")
    replication: Mapped[str] = mapped_column(String(50), default="")
    healthy: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_healthcheck_at: Mapped[str] = mapped_column(String(50), default="")
