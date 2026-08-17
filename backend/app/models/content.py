from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

SERIES_KINDS = ("documentary", "cartoon")
SERIES_STATUSES = ("planned", "in_progress", "produced", "review", "approved", "published", "archived")
EPISODE_STATUSES = ("planned", "scripted", "produced", "localized", "assembled", "review", "approved", "published")


class Series(Base, TimestampMixin):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    topic: Mapped[str] = mapped_column(String(1000), default="")
    kind: Mapped[str] = mapped_column(String(20), default="documentary")
    status: Mapped[str] = mapped_column(String(30), default="planned")
    planned_episodes: Mapped[int] = mapped_column(Integer, default=1)
    language: Mapped[str] = mapped_column(String(10), default="fr")
    continuity_pack_id: Mapped[int] = mapped_column(ForeignKey("continuity_packs.id"), nullable=True)
    business_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    production_cost: Mapped[float] = mapped_column(default=0.0, nullable=False)


class Episode(Base, TimestampMixin):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=False)
    number: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(30), default="planned")
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    target_duration_seconds: Mapped[int] = mapped_column(Integer, default=90)
    script: Mapped[str] = mapped_column(nullable=True)
    narration: Mapped[str] = mapped_column(nullable=True)


class Scene(Base, TimestampMixin):
    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(default="")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=10)
    beat: Mapped[str] = mapped_column(String(50), default="")  # cold_open|intro|build|climax|teaser|song_in|song_out


class Segment(Base, TimestampMixin):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[int] = mapped_column(ForeignKey("scenes.id"), index=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=8)
    content_type: Mapped[str] = mapped_column(String(30), default="visual")  # visual|voice|music|sfx|caption
    prompt: Mapped[str] = mapped_column(default="")
    generated_content: Mapped[str] = mapped_column(default="")
