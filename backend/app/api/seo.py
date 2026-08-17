from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import ABTestVariant, Episode, SEOPackage, Series, ShortsPackage, User

router = APIRouter(prefix="/seo", tags=["seo"])


def _episode_owned(user: User, db: Session, episode_id: int) -> Episode:
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(404, "Episode not found")
    series = db.get(Series, ep.series_id)
    if series.workspace_id != user.workspace_id:
        raise HTTPException(404, "Episode not found")
    return ep


@router.get("/episodes/{episode_id}")
def get_seo_package(episode_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _episode_owned(user, db, episode_id)
    packages = db.scalars(select(SEOPackage).where(SEOPackage.episode_id == episode_id)).all()
    shorts = db.scalars(select(ShortsPackage).where(ShortsPackage.episode_id == episode_id)).all()
    ab = db.scalars(select(ABTestVariant).where(ABTestVariant.episode_id == episode_id)).all()
    return {
        "seo": [
            {"language": s.language, "title": s.title, "description": s.description, "tags": s.tags,
             "hashtags": s.hashtags, "chapters": s.chapters, "keywords": s.keywords, "metadata": s.metadata_json}
            for s in packages
        ],
        "shorts": [
            {"platform": s.platform, "captions": s.captions, "cta": s.cta, "metadata": s.metadata_json}
            for s in shorts
        ],
        "ab_tests": [{"field": v.field, "variant": v.variant, "score": v.score} for v in ab],
    }


@router.post("/episodes/{episode_id}/ab-test")
def add_ab_variant(episode_id: int, field: str = "title", variant: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ep = _episode_owned(user, db, episode_id)
    v = ABTestVariant(episode_id=ep.id, field=field, variant=variant)
    db.add(v)
    db.commit()
    return {"ok": True, "id": v.id}
