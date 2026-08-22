from __future__ import annotations

import logging
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger("video_factory.cleanup")

# Task types whose produced files are intermediate (per-segment media). Once the
# series is finalized, BOTH the stored asset (bucket) and the local file are
# removed — they are never needed again.
INTERMEDIATE_MEDIA_TASK_TYPES = {
    "image_generate",
    "video_generate",
    "stock_video",
    "tts_voice",
    "music_generate",
    "clip_assembly",
    "subtitle",
}

# Final deliverables. The stored asset (bucket) is KEPT — it is what you
# download for YouTube/TikTok/etc. — but the local server-side copy is removed
# to save disk (the bucket becomes the single source of truth).
FINAL_MEDIA_TASK_TYPES = {
    "final_assembly",
    "shorts_package",
}


def cleanup_series_intermediates(db: Session, series_id: int) -> int:
    """Clean media files for a finalized series; return bytes freed.

    - Intermediates: delete stored asset (object + row + used_bytes) AND local file.
    - Final video / shorts: keep the stored asset (bucket), delete only the local file.

    Checkpoint rows are always preserved (re-run/idempotency metadata). Never raises.
    """
    from app.models import Checkpoint, JobTask

    freed = 0

    inter = db.scalars(
        select(Checkpoint)
        .join(JobTask, Checkpoint.task_id == JobTask.id)
        .where(JobTask.series_id == series_id, JobTask.task_type.in_(INTERMEDIATE_MEDIA_TASK_TYPES))
    ).all()
    for cp in inter:
        freed += _delete_asset_and_local(db, cp)

    final = db.scalars(
        select(Checkpoint)
        .join(JobTask, Checkpoint.task_id == JobTask.id)
        .where(JobTask.series_id == series_id, JobTask.task_type.in_(FINAL_MEDIA_TASK_TYPES))
    ).all()
    for cp in final:
        _delete_local_only(cp)

    db.commit()
    return freed


def _delete_asset_and_local(db: Session, cp) -> int:
    """Delete a checkpoint's stored asset(s) + local file. Return bytes freed."""
    from app.models import Asset, StorageBackend
    from app.registries.storage_registry import build_adapter

    freed = 0
    if cp.content_ref:
        assets = db.scalars(select(Asset).where(Asset.path == cp.content_ref)).all()
        for asset in assets:
            try:
                backend = db.get(StorageBackend, asset.storage_id)
                if backend:
                    build_adapter(backend).delete(asset.path)
                    backend.used_bytes = max(0, backend.used_bytes - asset.size)
            except Exception as exc:  # noqa: BLE001
                # Log loudly: the asset row is still dropped below, but the
                # object remains in the bucket (e.g. missing DeleteObject perm).
                logger.error(
                    "storage delete failed for %s (kind=%s): %s",
                    asset.path, backend.kind if backend else "?", exc,
                )
            freed += asset.size
            db.delete(asset)
    _delete_local_only(cp)
    return freed


def _delete_local_only(cp) -> None:
    """Remove the local provider output file referenced by a checkpoint."""
    local = (cp.metadata_json or {}).get("local_path")
    if local and os.path.exists(local):
        try:
            os.remove(local)
        except OSError as exc:  # noqa: BLE001
            logger.warning("local delete failed for %s: %s", local, exc)
