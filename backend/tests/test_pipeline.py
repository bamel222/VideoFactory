from __future__ import annotations

import pytest


def test_dry_run_produces_report_without_video(client, owner_token, seeded_series):
    r = client.post(f"/api/v1/series/{seeded_series}/dry-run", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, r.text
    report = r.json()["report"]
    assert report["series_id"] == seeded_series
    assert report["tasks"] > 0
    assert report["ready_to_launch"] is True
    assert report["missing_providers"] == []
    assert "estimated_cost" in report["budget"]
    # Must NOT have generated any checkpoint / video
    cps = client.get(f"/api/v1/jobs/series/{seeded_series}/checkpoints", headers={"Authorization": f"Bearer {owner_token}"})
    assert cps.json() == []


def test_full_pipeline_generates_checkpoints_and_seo(client, owner_token, seeded_series):
    r = client.post(
        f"/api/v1/series/{seeded_series}/run",
        json={"series_id": seeded_series, "dry_run": False},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "done"
    assert body["done_tasks"] == body["total_tasks"]
    assert body["total_tasks"] > 10

    # Checkpoints created
    cps = client.get(f"/api/v1/jobs/series/{seeded_series}/checkpoints", headers={"Authorization": f"Bearer {owner_token}"})
    assert len(cps.json()) > 10

    # SEO + shorts persisted (use the first episode id of this series)
    series = client.get(f"/api/v1/series/{seeded_series}", headers={"Authorization": f"Bearer {owner_token}"}).json()
    episode_id = series["episodes"][0]["id"]
    seo = client.get(f"/api/v1/seo/episodes/{episode_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert seo.json()["seo"], "SEO package should be persisted"
    assert seo.json()["shorts"], "Shorts packages should be persisted"

    # Episodes in review
    queue = client.get("/api/v1/review/queue", headers={"Authorization": f"Bearer {owner_token}"})
    assert len(queue.json()) >= 1


def test_pipeline_is_idempotent(client, owner_token, seeded_series):
    client.post(
        f"/api/v1/series/{seeded_series}/run",
        json={"series_id": seeded_series, "dry_run": False},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    first = client.get(f"/api/v1/jobs/series/{seeded_series}/checkpoints", headers={"Authorization": f"Bearer {owner_token}"})
    count_before = len(first.json())

    # Re-run: tasks reuse existing checkpoints, no new provider calls
    r = client.post(
        f"/api/v1/series/{seeded_series}/run",
        json={"series_id": seeded_series, "dry_run": False},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.json()["status"] == "done"
    after = client.get(f"/api/v1/jobs/series/{seeded_series}/checkpoints", headers={"Authorization": f"Bearer {owner_token}"})
    assert len(after.json()) == count_before


def test_resume_after_interruption(client, owner_token, seeded_series):
    """Interrompre un job, relancer, reprendre au dernier checkpoint sans perte."""
    from app.core.db import SessionLocal
    from app.models import JobTask

    # Simulate an interruption: mark every pending task as failed as if the run was killed
    r = client.post(
        f"/api/v1/series/{seeded_series}/run",
        json={"series_id": seeded_series, "dry_run": False},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.json()["status"] == "done"

    db = SessionLocal()
    # Simulate "re-run from interrupted state": reset a few tasks to pending
    tasks = db.query(JobTask).filter(JobTask.series_id == seeded_series).order_by(JobTask.id.desc()).limit(5).all()
    for t in tasks:
        t.status = "pending"
        t.error = "interrupted"
    db.commit()
    db.close()

    # Resume: only the reset tasks should be re-executed, the rest reuse checkpoints
    r = client.post(f"/api/v1/series/{seeded_series}/resume", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "done"

    # All tasks eventually succeeded
    db = SessionLocal()
    remaining = db.query(JobTask).filter(JobTask.series_id == seeded_series, JobTask.status != "succeeded").count()
    db.close()
    assert remaining == 0


def test_continuity_pack_auto_created(client, owner_token, seeded_series):
    r = client.get(f"/api/v1/series/{seeded_series}/continuity-pack", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200
    pack = r.json()
    assert pack["exists"] is True
    assert pack["negative_rules"], "negative rules should exist"
