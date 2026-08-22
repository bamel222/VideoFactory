from __future__ import annotations

import json

from app.orchestrator.seo_export import build_episode_seo_payload, seo_object_key
from app.models import Series, Episode


def test_seo_object_key():
    s = Series(title="L'histoire des océans", topic="")
    e = Episode(number=2)
    assert seo_object_key(s, e) == "series/l-histoire-des-oceans/episode_2/seo.json"


def test_build_seo_payload_empty(client, owner_token, seeded_series):
    """Build a payload for a seeded episode (no SEO/shorts yet -> empty lists)."""
    from app.core.db import SessionLocal
    from app.models import Episode

    db = SessionLocal()
    try:
        ep = db.query(Episode).filter(Episode.series_id == seeded_series).first()
        assert ep is not None, "seeded series should have an episode"
        series = db.query(Series).filter(Series.id == ep.series_id).first()
        payload = build_episode_seo_payload(db, series, ep)
        assert payload["series"] == series.title
        assert payload["episode"] == ep.number
        assert isinstance(payload["seo"], list)
        assert isinstance(payload["shorts"], list)
        # Must be JSON-serializable
        json.dumps(payload)
    finally:
        db.close()
