from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import JobRun, JobTask, Series, User
from app.orchestrator.checkpoints import get_series_checkpoints

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    series_ids = db.scalars(select(Series.id).where(Series.workspace_id == user.workspace_id)).all()
    runs = db.scalars(select(JobRun).where(JobRun.series_id.in_(series_ids)).order_by(JobRun.id.desc())).all()
    return [
        {
            "id": r.id, "series_id": r.series_id, "kind": r.kind, "status": r.status,
            "dry_run": r.dry_run, "total_tasks": r.total_tasks, "done_tasks": r.done_tasks,
            "total_cost": r.total_cost, "error": r.error, "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = db.get(JobRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    # Enforce workspace isolation: a run is only visible within its own workspace.
    series = db.get(Series, run.series_id)
    if not series or series.workspace_id != user.workspace_id:
        raise HTTPException(404, "Run not found")
    tasks = db.scalars(select(JobTask).where(JobTask.job_run_id == run.id).order_by(JobTask.sequence)).all()
    return {
        "id": run.id, "status": run.status, "kind": run.kind, "dry_run": run.dry_run,
        "total_tasks": run.total_tasks, "done_tasks": run.done_tasks, "total_cost": run.total_cost,
        "error": run.error,
        "tasks": [
            {
                "id": t.id, "task_type": t.task_type, "queue": t.queue, "status": t.status,
                "sequence": t.sequence, "cost": t.cost, "provider_id": t.provider_id,
                "error": t.error, "episode_id": t.episode_id, "checkpoint_id": t.checkpoint_id,
                "payload": t.payload,
            }
            for t in tasks
        ],
    }


@router.get("/series/{series_id}/checkpoints")
def series_checkpoints(series_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    series = db.get(Series, series_id)
    if not series or series.workspace_id != user.workspace_id:
        raise HTTPException(404, "Series not found")
    return [
        {
            "id": c.id, "task_id": c.task_id, "kind": c.kind, "provider": c.provider,
            "content_ref": c.content_ref, "cost": c.cost, "hash": c.hash,
            "version": c.version, "valid": c.valid, "created_at": c.created_at.isoformat(),
            "metadata": c.metadata_json,
        }
        for c in get_series_checkpoints(db, series_id)
    ]
