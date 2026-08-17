from __future__ import annotations

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Episode, JobTask, Series


def _create_series(client, token, kind, **overrides):
    payload = {"title": "Série test", "topic": "un sujet long", "kind": kind, "planned_episodes": 1, "language": "fr"}
    payload.update(overrides)
    r = client.post("/api/v1/series", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _tasks_for(series_id: int) -> list[JobTask]:
    db = SessionLocal()
    try:
        return list(db.scalars(select(JobTask).where(JobTask.series_id == series_id).order_by(JobTask.sequence)).all())
    finally:
        db.close()


def _task_types_for(series_id: int) -> set[str]:
    return {t.task_type for t in _tasks_for(series_id)}


def test_default_modes_by_kind(client, owner_token):
    doc_id = _create_series(client, owner_token, "documentary")
    cart_id = _create_series(client, owner_token, "cartoon")

    db = SessionLocal()
    try:
        doc = db.get(Series, doc_id)
        cart = db.get(Series, cart_id)
        assert doc.effective_mode() == "images"
        assert cart.effective_mode() == "video"
        assert doc.fact_check_enabled is True  # documentaire: toujours fact-checké
        assert cart.fact_check_enabled is False  # cartoon: fiction par défaut
    finally:
        db.close()


def test_explicit_modes_are_stored(client, owner_token):
    doc_video = _create_series(client, owner_token, "documentary", generation_mode="video")
    cart_images = _create_series(client, owner_token, "cartoon", generation_mode="images")
    db = SessionLocal()
    try:
        assert db.get(Series, doc_video).effective_mode() == "video"
        assert db.get(Series, cart_images).effective_mode() == "images"
    finally:
        db.close()


def test_invalid_mode_rejected(client, owner_token):
    r = client.post(
        "/api/v1/series",
        json={"title": "x", "kind": "documentary", "generation_mode": "3d"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 422


def test_invalid_duration_rejected(client, owner_token):
    for bad in (10, 60):
        r = client.post(
            "/api/v1/series",
            json={"title": "x", "kind": "documentary", "duration_minutes": bad},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 422


def test_segment_task_type_by_mode(client, owner_token):
    # Documentaire images -> image_generate ; vidéo -> stock_video
    doc_img = _create_series(client, owner_token, "documentary", generation_mode="images")
    doc_vid = _create_series(client, owner_token, "documentary", generation_mode="video")
    # Cartoon vidéo -> video_generate ; images -> image_generate
    cart_vid = _create_series(client, owner_token, "cartoon", generation_mode="video")
    cart_img = _create_series(client, owner_token, "cartoon", generation_mode="images")

    assert "image_generate" in _task_types_for(doc_img)
    assert "stock_video" in _task_types_for(doc_vid)
    assert "video_generate" in _task_types_for(cart_vid)
    assert "image_generate" in _task_types_for(cart_img)
    # No cross-mode leak
    assert "stock_video" not in _task_types_for(doc_img)
    assert "image_generate" not in _task_types_for(doc_vid)


def test_fact_check_toggle_for_cartoon(client, owner_token):
    fiction = _create_series(client, owner_token, "cartoon")
    factual = _create_series(client, owner_token, "cartoon", based_on_facts=True)

    assert "fact_check" not in _task_types_for(fiction)
    assert "fact_check" in _task_types_for(factual)


def test_documentary_always_fact_checked(client, owner_token):
    doc_id = _create_series(client, owner_token, "documentary")
    assert "fact_check" in _task_types_for(doc_id)


def test_duration_26min_scales_segments(client, owner_token):
    series_id = _create_series(client, owner_token, "documentary", generation_mode="images", duration_minutes=26)
    db = SessionLocal()
    try:
        ep = db.scalar(select(Episode).where(Episode.series_id == series_id))
        # 26 min = 1560 s ; ~12 s par segment -> ~130 segments visuels
        assert 120 <= ep.target_duration_seconds <= 1560
        seg_tasks = db.scalars(
            select(JobTask).where(JobTask.series_id == series_id, JobTask.task_type == "image_generate")
        ).all()
        assert len(seg_tasks) >= 100
        assert len(seg_tasks) <= 170
    finally:
        db.close()


def test_main_language_voiceover_planned(client, owner_token):
    doc_id = _create_series(client, owner_token, "documentary")
    tasks = _tasks_for(doc_id)
    narration_tts = [t for t in tasks if t.task_type == "tts_voice" and (t.payload or {}).get("subtype") == "narration"]
    assert narration_tts, "la voix principale (narration TTS) doit être planifiée"
