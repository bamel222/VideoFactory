from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.audit import audit_log
from app.core.security import require_permission
from app.models import Episode, ReviewRecord, SEOPackage, Series, ShortsPackage, User
from app.schemas.review import ReviewDecision

router = APIRouter(prefix="/review", tags=["review"])


def _episode(user: User, db: Session, episode_id: int) -> Episode:
    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(404, "Episode not found")
    series = db.get(Series, ep.series_id)
    if series.workspace_id != user.workspace_id:
        raise HTTPException(404, "Episode not found")
    return ep


@router.get("/queue")
def review_queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    series_ids = db.scalars(select(Series.id).where(Series.workspace_id == user.workspace_id)).all()
    eps = db.scalars(
        select(Episode).where(Episode.series_id.in_(series_ids), Episode.status.in_(("review", "produced", "localized", "assembled")))
    ).all()
    return [
        {
            "episode_id": e.id, "title": e.title, "number": e.number, "status": e.status,
            "series_id": e.series_id, "is_final": e.is_final, "script": e.script, "narration": e.narration,
        }
        for e in eps
    ]


@router.get("/episodes/{episode_id}")
def episode_review(episode_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ep = _episode(user, db, episode_id)
    seo = db.scalars(select(SEOPackage).where(SEOPackage.episode_id == ep.id)).all()
    shorts = db.scalars(select(ShortsPackage).where(ShortsPackage.episode_id == ep.id)).all()
    history = db.scalars(
        select(ReviewRecord).where(ReviewRecord.episode_id == ep.id).order_by(ReviewRecord.id.desc())
    ).all()
    return {
        "episode": {"id": ep.id, "number": ep.number, "title": ep.title, "status": ep.status, "script": ep.script, "narration": ep.narration},
        "seo": [{"language": s.language, "title": s.title, "description": s.description, "tags": s.tags, "hashtags": s.hashtags, "chapters": s.chapters} for s in seo],
        "shorts": [{"platform": s.platform, "captions": s.captions, "cta": s.cta, "asset_path": s.asset_path} for s in shorts],
        "history": [{"version": h.version, "status": h.status, "comment": h.comment, "user_id": h.user_id, "created_at": h.created_at.isoformat()} for h in history],
    }


@router.post("/episodes/{episode_id}/decide")
def decide(
    episode_id: int,
    body: ReviewDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not require_permission(user.role, "review.operational"):
        raise HTTPException(403, "Admin or Owner only")
    ep = _episode(user, db, episode_id)
    if body.status not in ("approved", "revision"):
        raise HTTPException(400, "status must be approved or revision")
    record = ReviewRecord(episode_id=ep.id, user_id=user.id, status=body.status, comment=body.comment)
    db.add(record)
    if body.status == "approved":
        ep.status = "approved"
    else:
        ep.status = "review"
    db.commit()
    audit_log(db, user.id, "review.decide", "episode", ep.id, {"status": body.status, "comment": body.comment}, request.client.host if request.client else None)
    return {"ok": True, "episode_id": ep.id, "status": ep.status}
