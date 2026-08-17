from __future__ import annotations

from pydantic import BaseModel


class ReviewDecision(BaseModel):
    status: str  # approved | revision
    comment: str = ""


class PublishRequest(BaseModel):
    episode_id: int
    platforms: list[str] = []
