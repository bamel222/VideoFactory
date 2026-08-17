from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import require_permission
from app.models import BudgetForecast, Series, User

router = APIRouter(prefix="/monetization", tags=["monetization"])


def _score_subject(topic: str, kind: str, languages: list[str], duration_min: float, risk_of_rights: float) -> float:
    """Heuristic business score: trend + languages + speed vs risk + cost."""
    import hashlib

    trend = 0.5 + (int(hashlib.sha1(topic.encode()).hexdigest(), 16) % 100) / 200.0
    lang_bonus = min(len(languages) * 0.1, 0.5)
    speed = min(120.0 / max(duration_min, 1.0), 2.0)
    risk_penalty = risk_of_rights
    score = (trend * 0.4 + lang_bonus * 0.3 + speed * 0.2) * (1.0 - risk_penalty)
    return round(min(max(score, 0.0), 1.0), 3)


@router.post("/score")
def score_subject(topic: str, kind: str = "documentary", languages: list[str] = ["fr"], duration_min: float = 2.0, risk_of_rights: float = 0.1, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Score a potential subject before creating a series."""
    return {
        "topic": topic,
        "score": _score_subject(topic, kind, languages, duration_min, risk_of_rights),
        "components": {"trend": 0.5, "languages": len(languages), "duration_min": duration_min, "risk": risk_of_rights},
        "recommendation": "prioritize" if _score_subject(topic, kind, languages, duration_min, risk_of_rights) > 0.6 else "review",
    }


@router.get("/priorities")
def priorities(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Rank existing series by business potential / production cost."""
    if not require_permission(user.role, "series.manage"):
        raise HTTPException(403, "Owner or Admin only")
    series = db.scalars(select(Series).where(Series.workspace_id == user.workspace_id)).all()
    rows = []
    for s in series:
        fc = db.scalar(select(BudgetForecast).where(BudgetForecast.series_id == s.id).order_by(BudgetForecast.id.desc()))
        cost = fc.estimated_cost if fc else s.production_cost
        ratio = (s.business_score / max(cost, 0.001)) if cost > 0 else (s.business_score * 10)
        rows.append({
            "series_id": s.id, "title": s.title, "kind": s.kind, "status": s.status,
            "business_score": s.business_score, "production_cost": round(cost, 4),
            "value_ratio": round(ratio, 3),
        })
    rows.sort(key=lambda r: r["value_ratio"], reverse=True)
    return rows
