from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import require_permission
from app.models import BudgetForecast, Series, User

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/billing")
def billing_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "billing.manage"):
        raise HTTPException(403, "Owner only")
    series_ids = db.scalars(select(Series.id).where(Series.workspace_id == user.workspace_id)).all()
    forecasts = db.scalars(select(BudgetForecast).where(BudgetForecast.series_id.in_(series_ids))).all()
    total_cost = sum(f.estimated_cost for f in forecasts)
    total_minutes = sum(f.minutes_video for f in forecasts)
    return {
        "plan": "free-first",
        "series_forecasted": len(forecasts),
        "total_estimated_cost": round(total_cost, 4),
        "total_minutes": round(total_minutes, 2),
        "currency": "USD",
    }
