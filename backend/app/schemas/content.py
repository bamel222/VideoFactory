from __future__ import annotations

from pydantic import BaseModel, Field


class SeriesCreate(BaseModel):
    title: str = Field(max_length=500)
    topic: str = Field(default="", max_length=3000)
    kind: str = "documentary"
    planned_episodes: int = 1
    language: str = "fr"


class SeriesOut(BaseModel):
    id: int
    title: str
    topic: str
    kind: str
    status: str
    planned_episodes: int
    language: str
    business_score: float
    production_cost: float


class DryRunRequest(BaseModel):
    series_id: int


class PipelineRequest(BaseModel):
    series_id: int
    dry_run: bool = False
