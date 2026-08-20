from __future__ import annotations

import time

from app.core import redis as redis_store
from app.core.db import session_scope
from app.registries.provider_registry import ProviderRegistry


def process_queue(queue: str) -> None:
    payload = redis_store.dequeue(queue, timeout_seconds=1)
    if payload is None:
        return
    task_id = payload.get("task_id")
    if not task_id:
        return
    with session_scope() as db:
        from app.agents.base import execute_task
        from app.models import JobTask, Series
        from app.orchestrator.fallback import execute_with_fallback
        from app.registries.capability_matrix import role_for_task

        task = db.get(JobTask, task_id)
        if not task:
            return
        series = db.get(Series, task.series_id)
        registry = ProviderRegistry(db, series.workspace_id if series else 0)
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
        except Exception as exc:  # noqa: BLE001
            task.status = "failed"
            task.error = str(exc)[:2000]
            db.commit()


def run_forever() -> None:
    queues = ["script", "audio", "image", "video", "montage", "seo", "qa", "research", "translation", "licensing"]
    while True:
        for q in queues:
            process_queue(q)
        time.sleep(0.2)


if __name__ == "__main__":
    print("Worker started. Queues: script, audio, image, video, montage, seo, qa, research, translation, licensing")
    run_forever()
