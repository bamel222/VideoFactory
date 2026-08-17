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
        from app.models import JobTask
        from app.registries.capability_matrix import role_for_task

        task = db.get(JobTask, task_id)
        if not task:
            return
        series = db.get(__import__("app.models", fromlist=["Series"]).Series, task.series_id)
        registry = ProviderRegistry(db, series.workspace_id if series else 0)
        role = role_for_task(task.task_type)
        provider = registry.select(role, {"language": (task.payload or {}).get("language")})
        if provider is None:
            task.status = "failed"
            task.error = "No provider"
            return
        execute_task(db, task, provider)


def run_forever() -> None:
    queues = ["script", "audio", "image", "video", "montage", "seo", "qa", "research", "translation", "licensing"]
    while True:
        for q in queues:
            process_queue(q)
        time.sleep(0.2)


if __name__ == "__main__":
    print("Worker started. Queues: script, audio, image, video, montage, seo, qa, research, translation, licensing")
    run_forever()
