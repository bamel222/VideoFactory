"""Manual cleanup script: delete intermediate media files of a series.

Usage (from backend/ or via docker):
    python -m app.scripts.cleanup_series <series_id>

Deletes intermediate assets (images/clips/audio/raw/subtitles) from BOTH the
storage bucket and local disk, keeping the final video + shorts in the bucket.
Prints detailed progress so S3 delete failures are visible.
"""
from __future__ import annotations

import sys

from app.core.db import SessionLocal, init_db
from app.orchestrator.cleanup import (
    FINAL_MEDIA_TASK_TYPES,
    INTERMEDIATE_MEDIA_TASK_TYPES,
    _delete_asset_and_local,
    _delete_local_only,
)
from app.models import Checkpoint, JobTask

from sqlalchemy import select


def run(series_id: int) -> None:
    init_db()
    db = SessionLocal()
    try:
        inter = db.scalars(
            select(Checkpoint)
            .join(JobTask, Checkpoint.task_id == JobTask.id)
            .where(JobTask.series_id == series_id, JobTask.task_type.in_(INTERMEDIATE_MEDIA_TASK_TYPES))
        ).all()
        final = db.scalars(
            select(Checkpoint)
            .join(JobTask, Checkpoint.task_id == JobTask.id)
            .where(JobTask.series_id == series_id, JobTask.task_type.in_(FINAL_MEDIA_TASK_TYPES))
        ).all()

        print(f"Intermediaires a supprimer: {len(inter)} checkpoints")
        print(f"Finaux a conserver (local seulement): {len(final)} checkpoints")

        freed = 0
        for i, cp in enumerate(inter, 1):
            freed += _delete_asset_and_local(db, cp)
            print(f"  [{i}/{len(inter)}] task {cp.task_id} ({cp.kind}) — ok")

        for cp in final:
            _delete_local_only(cp)
            print(f"  [final] task {cp.task_id} — local supprime, bucket conserve")

        db.commit()
        print(f"\nTermine. {freed} octets liberes du bucket.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.scripts.cleanup_series <series_id>")
        sys.exit(1)
    run(int(sys.argv[1]))
