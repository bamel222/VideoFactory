from __future__ import annotations

import logging
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger("video_factory.cleanup")

# Task types whose produced files are intermediate (per-segment media) and safe
# to delete once the series is finalized. The final video (`final_assembly`),
# shorts (`shorts_package`) and SEO (`seo_package`, metadata only) are kept.
# Checkpoint ROWS are preserved (they hold re-run/idempotency metadata and are
# tiny); only the underlying files are removed.
INTERMEDIATE_MEDIA_TASK_TYPES = {
    "image_generate",
    "video_generate",
    "stock_video",
    "tts_voice",
    "music_generate",
    "clip_assembly",
    "subtitle",
}


def cleanup_series_intermediates(db: Session, series_id: int) -> int:
    """Delete intermediate media files for a finalized series; return bytes freed.

    Removes both the stored asset (object + row, decrementing used_bytes) and
    the local provider output file. Checkpoint rows are kept. Never raises.
    """
    from app.models import Asset, Checkpoint, JobTask, StorageBackend
    from app.registries.storage_registry import build_adapter

    checkpoints = db.scalars(
        select(Checkpoint)
        .join(JobTask, Checkpoint.task_id == JobTask.id)
        .where(JobTask.series_id == series_id, JobTask.task_type.in_(INTERMEDIATE_MEDIA_TASK_TYPES))
    ).all()

    freed = 0
    for cp in checkpoints:
        # 1) Stored assets (one row per backend replica sharing the same path).
        if cp.content_ref:
            assets = db.scalars(select(Asset).where(Asset.path == cp.content_ref)).all()
            for asset in assets:
                try:
                    backend = db.get(StorageBackend, asset.storage_id)
                    if backend:
                        build_adapter(backend).delete(asset.path)
                        backend.used_bytes = max(0, backend.used_bytes - asset.size)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("storage delete failed for %s: %s", asset.path, exc)
                freed += asset.size
                db.delete(asset)

        # 2) Local provider output file (MEDIA_ROOT).
        local = (cp.metadata_json or {}).get("local_path")
        if local and os.path.exists(local):
            try:
                os.remove(local)
            except OSError as exc:  # noqa: BLE001
                logger.warning("local delete failed for %s: %s", local, exc)

    db.commit()
    return freed
