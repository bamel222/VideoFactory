from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

GENERATION_MODES = ("images", "video")
MODE_LABELS = {
    "images": "Images fixes animées (Ken Burns) — photos/illustrations qui défilent en douceur avec narration, musique et sous-titres",
    "video": "Clips vidéo (stock ou IA) — montage dynamique composé de clips vidéo, proche d'un reportage télévisé",
}


class NotifyPrefs(BaseModel):
    """Notification channels selected at launch. Any combination is allowed;
    none of them ever blocks the pipeline."""

    email: bool = False
    discord: bool = False
    telegram: bool = False


class SeriesCreate(BaseModel):
    title: str = Field(max_length=500)
    topic: str = Field(default="", max_length=3000)
    kind: str = "documentary"
    planned_episodes: int = 1
    language: str = "fr"
    generation_mode: str = ""
    duration_minutes: int = 26
    based_on_facts: bool = False
    notify: NotifyPrefs | None = None

    @field_validator("duration_minutes")
    @classmethod
    def _check_duration(cls, v: int) -> int:
        if not (24 <= v <= 28):
            raise ValueError("duration_minutes doit être compris entre 24 et 28")
        return v

    @field_validator("kind")
    @classmethod
    def _check_kind(cls, v: str) -> str:
        if v not in ("documentary", "cartoon"):
            raise ValueError("kind doit être documentary ou cartoon")
        return v

    @field_validator("generation_mode")
    @classmethod
    def _check_mode(cls, v: str) -> str:
        if v and v not in GENERATION_MODES:
            raise ValueError("generation_mode doit être images ou video")
        return v


class SeriesOut(BaseModel):
    id: int
    title: str
    topic: str
    kind: str
    status: str
    planned_episodes: int
    language: str
    generation_mode: str
    duration_minutes: int
    fact_check_enabled: bool
    business_score: float
    production_cost: float


class DryRunRequest(BaseModel):
    series_id: int


class PipelineRequest(BaseModel):
    series_id: int
    dry_run: bool = False
    notify: NotifyPrefs | None = None
