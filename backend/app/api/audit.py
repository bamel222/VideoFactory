from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import require_permission
from app.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    action: str | None = Query(None),
    resource: str | None = Query(None),
    limit: int = Query(100, le=500),
):
    if not require_permission(user.role, "audit.read"):
        raise HTTPException(403, "Owner or Admin only")
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if action:
        q = q.where(AuditLog.action == action)
    if resource:
        q = q.where(AuditLog.resource == resource)
    return [
        {
            "id": a.id, "user_id": a.user_id, "action": a.action, "resource": a.resource,
            "resource_id": a.resource_id, "details": a.details_json, "ip": a.ip,
            "created_at": a.created_at.isoformat(),
        }
        for a in db.scalars(q).all()
    ]
