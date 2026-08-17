from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DryRun, Episode, JobTask, Series
from app.registries.capability_matrix import role_for_task


def run_dry_run(db: Session, series: Series) -> DryRun:
    """Simulate production without calling any provider."""
    tasks = db.scalars(
        select(JobTask).where(JobTask.series_id == series.id).order_by(JobTask.sequence)
    ).all()
    episodes = db.scalars(select(Episode).where(Episode.series_id == series.id)).all()

    from app.registries.provider_registry import ProviderRegistry

    registry = ProviderRegistry(db, series.workspace_id)

    by_role: dict[str, dict] = {}
    missing: list[str] = []
    for task in tasks:
        role = role_for_task(task.task_type)
        if role is None:
            continue
        entry = by_role.setdefault(role, {"count": 0, "provider": None, "quota_ok": True})
        entry["count"] += 1
        if entry["provider"] is None:
            provider = registry.select(role, task.payload.get("language") and {"language": task.payload["language"]} or None)
            entry["provider"] = provider.name if provider else None
            if provider is None:
                entry["quota_ok"] = False
                missing.append(role)

    from app.orchestrator.budget import forecast_series

    forecast = forecast_series(db, series, language=series.language)

    report = {
        "series_id": series.id,
        "series_title": series.title,
        "kind": series.kind,
        "episodes": len(episodes),
        "tasks": len(tasks),
        "queues": sorted({t.queue for t in tasks}),
        "roles": by_role,
        "missing_providers": missing,
        "budget": {
            "minutes_video": forecast.minutes_video,
            "tts_chars": forecast.tts_chars,
            "translations": forecast.translations,
            "storage_gb": forecast.storage_gb,
            "gpu_hours": forecast.gpu_hours,
            "estimated_cost": forecast.estimated_cost,
        },
        "risks": forecast.risks,
        "quotas_ok": forecast.quotas_ok,
        "ready_to_launch": not missing and forecast.quotas_ok,
        "note": "Simulation terminée. Aucun provider n'a été appelé, aucune vidéo générée.",
    }

    dry = DryRun(series_id=series.id, report=report)
    db.add(dry)
    db.commit()
    db.refresh(dry)
    return dry
