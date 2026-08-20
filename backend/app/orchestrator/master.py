from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import execute_task
from app.core.audit import audit_log
from app.core.db import session_scope
from app.models import JobRun, JobTask, Series, User
from app.orchestrator.checkpoints import get_latest_valid
from app.orchestrator.fallback import execute_with_fallback
from app.registries.capability_matrix import role_for_task
from app.registries.provider_registry import ProviderRegistry


def run_pipeline(db: Session, series_id: int, dry_run: bool = False, requester: User | None = None) -> JobRun:
    """Execute all pending tasks of a series in dependency order (or simulate if dry_run).

    `requester` is the user who triggered the run; when provided (and not a dry
    run), per-episode + series-recap notifications are dispatched at the end.
    """
    series = db.get(Series, series_id)
    if not series:
        raise LookupError(f"Series {series_id} not found")

    from app.orchestrator.dryrun import run_dry_run

    if dry_run:
        dry = run_dry_run(db, series)
        return dry_report_as_run(db, series, dry.report)

    run = _get_or_create_run(db, series_id)
    registry = ProviderRegistry(db, series.workspace_id)
    tasks = db.scalars(
        select(JobTask).where(JobTask.series_id == series_id, JobTask.job_run_id == run.id).order_by(JobTask.sequence)
    ).all()

    run.status = "running"
    run.total_tasks = len(tasks)
    db.commit()

    done = 0
    for task in tasks:
        if task.status == "succeeded":
            done += 1
            continue
        if not _dependencies_satisfied(db, task):
            task.status = "skipped"
            task.error = "dependencies not satisfied"
            db.commit()
            continue

        # Idempotency: reuse existing valid checkpoint for same task
        existing = get_latest_valid(db, task.id)
        if existing and existing.valid:
            task.status = "succeeded"
            task.checkpoint_id = existing.id
            db.commit()
            done += 1
            continue

        role = role_for_task(task.task_type)
        try:
            task.status = "running"
            db.commit()

            def _run(provider) -> bool:
                execute_task(db, task, provider)
                return True

            execute_with_fallback(
                registry,
                role,
                {"language": (task.payload or {}).get("language")},
                _run,
            )
            done += 1
        except Exception as exc:  # noqa: BLE001
            task.status = "failed"
            task.error = str(exc)[:2000]
            db.commit()
            audit_log(db, None, "task.failed", "job_task", task.id, {"error": str(exc)})

    run.done_tasks = sum(1 for t in tasks if t.status == "succeeded")
    run.total_cost = sum(t.cost or 0.0 for t in tasks)
    failed = [t for t in tasks if t.status == "failed"]
    run.status = "failed" if failed else "done"
    if failed:
        run.error = f"{len(failed)} tâche(s) en échec"
    db.commit()
    db.refresh(run)

    from app.models import Episode

    if run.status == "done":
        for ep in db.scalars(select(Episode).where(Episode.series_id == series_id)).all():
            ep.status = "review"
        series.status = "produced"
        db.commit()

    # Non-blocking notifications (per-episode + recap). Never raises.
    if requester is not None and not dry_run:
        try:
            from app.notifications.dispatcher import notify_pipeline_outcome

            notify_pipeline_outcome(db, requester, series, tasks)
        except Exception:  # noqa: BLE001
            pass

    # Once fully successful, delete intermediate media files (keep final video
    # + shorts + SEO + checkpoint rows). Never raises; only on full success so
    # failed intermediates remain available for a retry.
    if requester is not None and not dry_run and run.status == "done":
        try:
            from app.orchestrator.cleanup import cleanup_series_intermediates

            cleanup_series_intermediates(db, series_id)
        except Exception:  # noqa: BLE001
            pass
    return run


def _get_or_create_run(db: Session, series_id: int) -> JobRun:
    run = db.scalar(
        select(JobRun)
        .where(JobRun.series_id == series_id, JobRun.kind == "pipeline")
        .order_by(JobRun.id.desc())
    )
    if run is None:
        run = JobRun(series_id=series_id, kind="pipeline", status="running")
        db.add(run)
        db.commit()
        db.refresh(run)
    else:
        run.status = "running"
        db.commit()
        db.refresh(run)
    return run


def _dependencies_satisfied(db: Session, task: JobTask) -> bool:
    if not task.depends_on:
        return True
    for dep_id in task.depends_on:
        dep = db.get(JobTask, dep_id)
        if dep is None or dep.status != "succeeded":
            return False
    return True


def dry_report_as_run(db: Session, series: Series, report: dict) -> JobRun:
    run = JobRun(
        series_id=series.id,
        kind="dry_run",
        status="done",
        dry_run=True,
        total_tasks=report.get("tasks", 0),
        done_tasks=report.get("tasks", 0),
        total_cost=report.get("budget", {}).get("estimated_cost", 0.0),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def resume_interrupted(db: Session, series_id: int) -> JobRun:
    """Resume the last interrupted run, skipping already-succeeded tasks."""
    return run_pipeline(db, series_id, dry_run=False)
