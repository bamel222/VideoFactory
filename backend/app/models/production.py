from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ContinuityPack(Base, TimestampMixin):
    __tablename__ = "continuity_packs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="")
    characters: Mapped[list] = mapped_column(JSON, default=list)  # [{name, traits, voice, ref}]
    voices: Mapped[list] = mapped_column(JSON, default=list)  # [{name, provider, ref}]
    style: Mapped[dict] = mapped_column(JSON, default=dict)
    palette: Mapped[list] = mapped_column(JSON, default=list)
    lut: Mapped[str] = mapped_column(String(255), default="")
    decors: Mapped[list] = mapped_column(JSON, default=list)
    sfx: Mapped[list] = mapped_column(JSON, default=list)
    music: Mapped[dict] = mapped_column(JSON, default=dict)
    prompts: Mapped[dict] = mapped_column(JSON, default=dict)
    validated_frames: Mapped[list] = mapped_column(JSON, default=list)
    negative_rules: Mapped[list] = mapped_column(JSON, default=list)


class BudgetForecast(Base, TimestampMixin):
    __tablename__ = "budget_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=False)
    minutes_video: Mapped[float] = mapped_column(Float, default=0.0)
    tts_chars: Mapped[int] = mapped_column(Integer, default=0)
    translations: Mapped[int] = mapped_column(Integer, default=0)
    storage_gb: Mapped[float] = mapped_column(Float, default=0.0)
    gpu_hours: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    quotas_ok: Mapped[bool] = mapped_column(default=True, nullable=False)
    risks: Mapped[list] = mapped_column(JSON, default=list)  # [{level, message}]


class DryRun(Base, TimestampMixin):
    __tablename__ = "dry_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=False)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
