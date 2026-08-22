from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import _slugify
from app.models import Episode, SEOPackage, Series, ShortsPackage


def build_episode_seo_payload(db: Session, series: Series, episode: Episode) -> dict:
    """Assemble a ready-to-paste SEO/shorts payload for one episode."""
    seo = db.scalars(select(SEOPackage).where(SEOPackage.episode_id == episode.id)).all()
    shorts = db.scalars(select(ShortsPackage).where(ShortsPackage.episode_id == episode.id)).all()

    return {
        "series": series.title,
        "episode": episode.number,
        "episode_title": episode.title or f"Épisode {episode.number}",
        "seo": [
            {
                "language": s.language,
                "title": s.title,
                "description": s.description,
                "tags": s.tags or [],
                "hashtags": s.hashtags or [],
                "keywords": s.keywords or [],
                "chapters": s.chapters or [],
                "thumbnail": s.thumbnail,
            }
            for s in seo
        ],
        "shorts": [
            {
                "platform": s.platform,
                "captions": s.captions,
                "cta": s.cta,
                "metadata": _safe_json(s.metadata_json),
            }
            for s in shorts
        ],
    }


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


def seo_object_key(series: Series, episode: Episode) -> str:
    """Object key for the per-episode seo.json, next to final.mp4 / short.mp4."""
    n = episode.number if episode.number else episode.id
    title = _slugify(series.title)
    return f"series/{title}/episode_{n}/seo.json"


def export_series_seo(db: Session, series: Series) -> int:
    """Write a seo.json for every episode into the storage registry.

    Returns the number of files written. Never raises (fire-and-forget at the
    end of a pipeline run).
    """
    from app.registries.storage_registry import StorageRegistry

    episodes = db.scalars(select(Episode).where(Episode.series_id == series.id).order_by(Episode.number)).all()
    if not episodes:
        return 0

    registry = StorageRegistry(db, series.workspace_id)
    written = 0
    for ep in episodes:
        try:
            payload = build_episode_seo_payload(db, series, ep)
            data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            registry.store_asset(seo_object_key(series, ep), data, kind="seo", content_type="application/json")
            written += 1
        except Exception:  # noqa: BLE001
            continue
    return written
