from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BudgetForecast, Episode, Scene, Segment, Series

CHARS_PER_SECOND = 15.0
SECONDS_PER_WORD_TTS = 5.0
GPU_FACTOR = 0.02  # gpu hours per video-second
STORAGE_MB_PER_VIDEO_SECOND = 0.3
AVG_WORDS_PER_SECOND = 2.0


def _total_duration(db: Session, series_id: int) -> float:
    ep_ids = db.scalars(select(Episode.id).where(Episode.series_id == series_id)).all()
    if not ep_ids:
        return 0.0
    sc_ids = db.scalars(select(Scene.id).where(Scene.episode_id.in_(ep_ids))).all()
    if not sc_ids:
        return 0.0
    total = sum(
        db.scalars(select(Segment.duration_seconds).where(Segment.scene_id.in_(sc_ids))).all()
    )
    return float(total)


def forecast_series(db: Session, series: Series, language: str = "fr", extra_languages: list[str] | None = None) -> BudgetForecast:
    duration = _total_duration(db, series.id)
    minutes = duration / 60.0
    episodes = db.scalars(select(Episode).where(Episode.series_id == series.id)).all()
    langs = {language, *(extra_languages or [])}

    tts_chars = int(duration * CHARS_PER_SECOND)
    translations = len(episodes) * (len(langs) - 1)
    storage_gb = duration * STORAGE_MB_PER_VIDEO_SECOND / 1024.0
    gpu_hours = duration * GPU_FACTOR

    # Cost estimate from provider registry
    from app.registries.provider_registry import ProviderRegistry

    registry = ProviderRegistry(db, series.workspace_id)
    cost = 0.0
    cost += tts_chars / 1000.0 * _provider_cost(registry, "tts")
    cost += gpu_hours * _provider_cost(registry, "video", 1.0)
    cost += storage_gb * _provider_cost(registry, "storage", 1.0)
    cost += translations * _provider_cost(registry, "translation")

    risks = _detect_risks(registry, duration, storage_gb, tts_chars)

    forecast = BudgetForecast(
        series_id=series.id,
        minutes_video=round(minutes, 2),
        tts_chars=tts_chars,
        translations=translations,
        storage_gb=round(storage_gb, 2),
        gpu_hours=round(gpu_hours, 2),
        estimated_cost=round(cost, 4),
        quotas_ok=not any(r["level"] == "critical" for r in risks),
        risks=risks,
    )
    db.add(forecast)
    db.commit()
    db.refresh(forecast)
    return forecast


def _provider_cost(registry, role: str, units: float = 1000.0) -> float:
    providers = [p for p in registry.list() if p.role == role and p.status == "active"]
    if not providers:
        return 0.0
    providers.sort(key=lambda p: p.priority)
    return providers[0].cost_per_unit * units


def _detect_risks(registry, duration: float, storage_gb: float, tts_chars: int) -> list[dict]:
    risks: list[dict] = []
    from app.registries.storage_registry import StorageRegistry

    storage_registry = StorageRegistry(registry.db, registry.workspace_id)
    active_storage = [s for s in storage_registry.list() if s.status == "active"]
    total_quota = sum(s.quota_bytes for s in active_storage)
    if total_quota and total_quota < storage_gb * 1024**3:
        risks.append({"level": "critical", "message": "Stockage insuffisant pour l'export final"})
    elif not active_storage:
        risks.append({"level": "warning", "message": "Aucun backend de stockage actif"})

    tts_providers = [p for p in registry.list() if p.role == "tts" and p.status == "active"]
    if tts_providers:
        max_quota = max(p.quota_total - p.quota_used for p in tts_providers)
        if max_quota < tts_chars:
            risks.append({"level": "critical", "message": "Quota TTS insuffisant pour la série"})
    else:
        risks.append({"level": "critical", "message": "Aucun provider TTS actif"})

    video_providers = [p for p in registry.list() if p.role == "video" and p.status == "active"]
    if not video_providers:
        risks.append({"level": "warning", "message": "Aucun provider vidéo actif (GPU requis probable)"})

    unstable = [p for p in registry.list() if p.status == "active" and not p.healthy]
    if unstable:
        risks.append({"level": "warning", "message": f"{len(unstable)} provider(s) instable(s)"})

    return risks
