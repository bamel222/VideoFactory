from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.audit import audit_log
from app.core.security import require_permission
from app.models import ContinuityPack, Episode, Scene, Segment, Series, User
from app.orchestrator.master import run_pipeline
from app.orchestrator.planner import generate_plan
from app.schemas.content import PipelineRequest, SeriesCreate

router = APIRouter(prefix="/series", tags=["series"])


def _check(user: User, series: Series) -> Series:
    if series.workspace_id != user.workspace_id:
        raise HTTPException(404, "Series not found")
    return series


def _serialize(s: Series) -> dict:
    return {
        "id": s.id, "title": s.title, "topic": s.topic, "kind": s.kind,
        "status": s.status, "planned_episodes": s.planned_episodes,
        "language": s.language, "generation_mode": s.effective_mode(),
        "duration_minutes": s.duration_minutes, "fact_check_enabled": s.fact_check_enabled,
        "business_score": s.business_score,
        "production_cost": s.production_cost, "continuity_pack_id": s.continuity_pack_id,
        "notify_email": s.notify_email,
        "notify_discord": s.notify_discord,
        "notify_telegram": s.notify_telegram,
    }


@router.get("")
def list_series(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        _serialize(s)
        for s in db.scalars(select(Series).where(Series.workspace_id == user.workspace_id).order_by(Series.id.desc())).all()
    ]


@router.post("")
def create_series(body: SeriesCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "series.manage"):
        raise HTTPException(403, "Owner or Admin only")
    mode = body.generation_mode or ("images" if body.kind == "documentary" else "video")
    # Documentary: fact-checking always enabled. Cartoon: only when based on real facts.
    fact_check = body.based_on_facts if body.kind == "cartoon" else True
    series = Series(
        workspace_id=user.workspace_id,
        title=body.title,
        topic=body.topic,
        kind=body.kind,
        planned_episodes=max(1, body.planned_episodes),
        language=body.language,
        generation_mode=mode,
        duration_minutes=max(24, min(28, body.duration_minutes)),
        fact_check_enabled=bool(fact_check),
        notify_email=bool(body.notify.email) if body.notify else False,
        notify_discord=bool(body.notify.discord) if body.notify else False,
        notify_telegram=bool(body.notify.telegram) if body.notify else False,
    )
    db.add(series)
    db.flush()
    generate_plan(db, series, language=body.language)
    db.commit()
    db.refresh(series)
    audit_log(db, user.id, "series.create", "series", series.id, {"title": series.title, "kind": series.kind, "mode": mode}, request.client.host if request.client else None)
    return _serialize(series)


@router.get("/{series_id}")
def get_series(series_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    series = _check(user, db.get(Series, series_id))
    episodes = []
    for ep in db.scalars(select(Episode).where(Episode.series_id == series.id).order_by(Episode.number)).all():
        scenes = []
        for sc in db.scalars(select(Scene).where(Scene.episode_id == ep.id).order_by(Scene.order)).all():
            segs = db.scalars(select(Segment).where(Segment.scene_id == sc.id).order_by(Segment.order)).all()
            scenes.append({
                "id": sc.id, "order": sc.order, "title": sc.title, "beat": sc.beat,
                "duration_seconds": sc.duration_seconds,
                "segments": [{"id": s.id, "order": s.order, "duration_seconds": s.duration_seconds, "content_type": s.content_type} for s in segs],
            })
        episodes.append({"id": ep.id, "number": ep.number, "title": ep.title, "status": ep.status, "is_final": ep.is_final, "scenes": scenes})
    return {
        "id": series.id, "title": series.title, "topic": series.topic, "kind": series.kind,
        "status": series.status, "language": series.language, "generation_mode": series.effective_mode(),
        "duration_minutes": series.duration_minutes, "fact_check_enabled": series.fact_check_enabled,
        "business_score": series.business_score,
        "production_cost": series.production_cost, "episodes": episodes,
    }


@router.post("/{series_id}/plan")
def plan_series(series_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    series = _check(user, db.get(Series, series_id))
    generate_plan(db, series, language=series.language)
    return {"ok": True, "series_id": series.id}


@router.post("/{series_id}/run", tags=["pipeline"])
def run_series(body: PipelineRequest, series_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "pipeline.run"):
        raise HTTPException(403, "Owner or Admin only")
    series = _check(user, db.get(Series, series_id))
    if body.notify is not None:
        series.notify_email = body.notify.email
        series.notify_discord = body.notify.discord
        series.notify_telegram = body.notify.telegram
        db.commit()
    audit_log(db, user.id, "pipeline.run", "series", series.id, {"dry_run": body.dry_run}, request.client.host if request.client else None)
    run = run_pipeline(db, series.id, dry_run=body.dry_run, requester=user)
    return {"job_run_id": run.id, "status": run.status, "dry_run": run.dry_run, "total_tasks": run.total_tasks, "done_tasks": run.done_tasks, "total_cost": run.total_cost}


@router.post("/{series_id}/dry-run")
def dry_run_series(series_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "pipeline.run"):
        raise HTTPException(403, "Owner or Admin only")
    series = _check(user, db.get(Series, series_id))
    from app.orchestrator.dryrun import run_dry_run

    audit_log(db, user.id, "pipeline.dryrun", "series", series.id, {}, request.client.host if request.client else None)
    dry = run_dry_run(db, series)
    return {"dry_run_id": dry.id, "report": dry.report}


@router.get("/{series_id}/continuity-pack")
def get_continuity_pack(series_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    series = _check(user, db.get(Series, series_id))
    pack = db.get(ContinuityPack, series.continuity_pack_id) if series.continuity_pack_id else None
    if not pack:
        return {"exists": False}
    return {
        "exists": True,
        "id": pack.id,
        "name": pack.name,
        "characters": pack.characters,
        "voices": pack.voices,
        "style": pack.style,
        "palette": pack.palette,
        "lut": pack.lut,
        "decors": pack.decors,
        "sfx": pack.sfx,
        "music": pack.music,
        "prompts": pack.prompts,
        "validated_frames": pack.validated_frames,
        "negative_rules": pack.negative_rules,
    }


@router.put("/{series_id}/continuity-pack")
def update_continuity_pack(series_id: int, body: dict, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "series.manage"):
        raise HTTPException(403, "Owner or Admin only")
    series = _check(user, db.get(Series, series_id))
    pack = db.get(ContinuityPack, series.continuity_pack_id) if series.continuity_pack_id else None
    if not pack:
        raise HTTPException(404, "Continuity pack not found (run plan first)")
    for field in ("characters", "voices", "style", "palette", "lut", "decors", "sfx", "music", "prompts", "validated_frames", "negative_rules"):
        if field in body:
            setattr(pack, field, body[field])
    db.commit()
    audit_log(db, user.id, "continuity_pack.update", "series", series.id, {}, request.client.host if request.client else None)
    return {"ok": True}


@router.post("/{series_id}/resume")
def resume_series(series_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "pipeline.run"):
        raise HTTPException(403, "Owner or Admin only")
    series = _check(user, db.get(Series, series_id))
    from app.orchestrator.master import resume_interrupted

    audit_log(db, user.id, "pipeline.resume", "series", series.id, {}, request.client.host if request.client else None)
    run = resume_interrupted(db, series.id)
    return {"job_run_id": run.id, "status": run.status, "done_tasks": run.done_tasks}
