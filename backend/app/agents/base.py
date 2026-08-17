from __future__ import annotations

import hashlib
import json
import os

from sqlalchemy.orm import Session

from app.agents.provider_client import build_provider_client
from app.core.audit import audit_log
from app.models import JobTask, Provider
from app.orchestrator.checkpoints import save_checkpoint
from app.registries.storage_registry import StorageRegistry

ESTIMATED_UNITS = {
    "research": 2000, "fact_check": 1000, "plan_series": 1500, "script_episode": 2000,
    "narration": 800, "translate": 400, "transcribe": 600,     "seo_package": 1200,
    "shorts_package": 1200, "qa_check": 600, "continuity_check": 600, "licensing_check": 600, "provenance_report": 400,
    "tts_voice": 500, "music_generate": 400, "image_generate": 1, "video_generate": 1,
    "clip_assembly": 1, "final_assembly": 1, "subtitle": 300, "audio_normalize": 1,
}


def _estimate_units(task: JobTask) -> float:
    return ESTIMATED_UNITS.get(task.task_type, 100.0)


def execute_task(db: Session, task: JobTask, provider: Provider) -> JobTask:
    """Run one task against a provider and persist a checkpoint. Idempotent via checkpoints."""
    client = build_provider_client(provider, db)
    result = client.generate(task)

    # Persist any produced file into the storage registry
    storage_ref = ""
    if isinstance(result, dict):
        path = result.get("path")
        if path:
            try:
                from app.models import Series

                series = db.get(Series, task.series_id)
                workspace_id = series.workspace_id if series else provider.workspace_id
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        data = f.read()
                    rel = f"series/{task.series_id}/task_{task.id}/{os.path.basename(path)}"
                    assets = StorageRegistry(db, workspace_id).store_asset(rel, data, kind=result.get("type", "file"))
                    storage_ref = assets[0].path if assets else path
                else:
                    storage_ref = path
            except Exception:
                storage_ref = path
        elif path:
            storage_ref = path

    content_hash = hashlib.sha256(json.dumps(result, default=str).encode()).hexdigest()
    units = _estimate_units(task)
    cost = provider.cost_per_unit * units if provider.cost_per_unit else 0.0

    cp = save_checkpoint(
        db,
        task_id=task.id,
        series_id=task.series_id,
        scene_id=task.scene_id,
        kind=result.get("type", "text") if isinstance(result, dict) else "text",
        content_ref=storage_ref,
        provider=provider.name,
        prompt=json.dumps(task.payload, ensure_ascii=False),
        cost=cost,
        content_hash=content_hash,
        metadata={"task_type": task.task_type, "local_path": path if isinstance(result, dict) and result.get("path") and os.path.exists(result.get("path")) else ""},
    )

    task.result = result
    task.status = "succeeded"
    task.provider_id = provider.id
    task.cost = cost
    task.checkpoint_id = cp.id
    db.commit()
    db.refresh(task)

    from app.agents.persist import persist_task_result

    persist_task_result(db, task)

    from app.registries.provider_registry import ProviderRegistry

    ProviderRegistry(db, provider.workspace_id).track_usage(provider, units, cost)
    audit_log(db, None, "task.succeeded", "job_task", task.id, {"task_type": task.task_type, "provider": provider.name, "cost": cost})
    return task
