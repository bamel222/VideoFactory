from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Checkpoint


def save_checkpoint(
    db: Session,
    *,
    task_id: int | None,
    series_id: int | None,
    scene_id: int | None,
    kind: str,
    content_ref: str,
    provider: str,
    prompt: str,
    cost: float,
    content_hash: str = "",
    storage_id: int | None = None,
    metadata: dict | None = None,
) -> Checkpoint:
    """Save a checkpoint, keeping the previous version if a regeneration occurs."""
    existing = None
    if task_id:
        existing = db.query(Checkpoint).filter(Checkpoint.task_id == task_id, Checkpoint.valid == True).first()  # noqa: E712

    cp = Checkpoint(
        task_id=task_id,
        series_id=series_id,
        scene_id=scene_id,
        kind=kind,
        content_ref=content_ref,
        provider=provider,
        prompt=prompt,
        cost=cost,
        hash=content_hash,
        storage_id=storage_id,
        metadata_json=metadata or {},
    )
    if existing:
        existing.valid = False
        cp.version = existing.version + 1
        cp.previous_id = existing.id
    else:
        cp.version = 1
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return cp


def get_latest_valid(db: Session, task_id: int) -> Checkpoint | None:
    return (
        db.query(Checkpoint)
        .filter(Checkpoint.task_id == task_id, Checkpoint.valid == True)  # noqa: E712
        .order_by(Checkpoint.version.desc())
        .first()
    )


def get_by_content(db: Session, kind: str, content_hash: str) -> Checkpoint | None:
    return (
        db.query(Checkpoint)
        .filter(Checkpoint.kind == kind, Checkpoint.hash == content_hash, Checkpoint.valid == True)  # noqa: E712
        .order_by(Checkpoint.version.desc())
        .first()
    )


def get_series_checkpoints(db: Session, series_id: int) -> list[Checkpoint]:
    return (
        db.query(Checkpoint)
        .filter(Checkpoint.series_id == series_id)
        .order_by(Checkpoint.id.asc())
        .all()
    )
