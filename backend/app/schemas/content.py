from __future__ import annotations

from pydantic import BaseModel


class SeriesCreate(BaseModel):
    title: str
    topic: str = ""
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
