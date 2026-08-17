from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.audit import audit_log
from app.core.security import require_permission
from app.models import Episode, LicenceRecord, Series, User

router = APIRouter(prefix="/publishing", tags=["publishing"])


@router.post("/episodes/{episode_id}")
def publish_episode(episode_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Publish only when: episode approved + full provenance with known licenses."""
    if not require_permission(user.role, "publication.final"):
        raise HTTPException(403, "Only the Owner can publish")

    ep = db.get(Episode, episode_id)
    if not ep:
        raise HTTPException(404, "Episode not found")
    series = db.get(Series, ep.series_id)
    if series.workspace_id != user.workspace_id:
        raise HTTPException(404, "Episode not found")

    if ep.status != "approved":
        raise HTTPException(409, "Episode must be approved before publishing")

    licences = db.scalars(select(LicenceRecord).where(LicenceRecord.series_id == series.id)).all()
    risks = [l for l in licences if l.risk in ("warn", "block")]
    if risks:
        blocked = [l for l in risks if l.risk == "block"]
        if blocked:
            raise HTTPException(409, "Publication blocked: licences risquées/inconnues présentes")

    ep.status = "published"
    series.status = "published"
    db.commit()
    audit_log(db, user.id, "publish.episode", "episode", ep.id, {"title": ep.title}, request.client.host if request.client else None)
    return {"ok": True, "episode_id": ep.id, "status": "published", "licences_checked": len(licences)}
