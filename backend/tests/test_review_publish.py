from __future__ import annotations

import pytest


def test_review_approve_publish_flow(client, owner_token, reviewer_token, seeded_series):
    # Produce the episode
    r = client.post(
        f"/api/v1/series/{seeded_series}/run",
        json={"series_id": seeded_series, "dry_run": False},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.json()["status"] == "done"

    episode_id = client.get(f"/api/v1/series/{seeded_series}", headers={"Authorization": f"Bearer {owner_token}"}).json()["episodes"][0]["id"]

    # Reviewer cannot decide approval (review.operational is admin/owner)
    r = client.post(
        f"/api/v1/review/episodes/{episode_id}/decide",
        json={"status": "approved", "comment": "ok"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert r.status_code == 403

    # Reviewer cannot publish
    r = client.post(f"/api/v1/publishing/episodes/{episode_id}", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert r.status_code == 403

    # Owner approves
    r = client.post(
        f"/api/v1/review/episodes/{episode_id}/decide",
        json={"status": "approved", "comment": "Approuvé"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.json()["status"] == "approved"

    # Owner publishes
    r = client.post(f"/api/v1/publishing/episodes/{episode_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "published"

    # Review history kept
    hist = client.get(f"/api/v1/review/episodes/{episode_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert len(hist.json()["history"]) >= 1


def test_cannot_publish_unapproved(client, owner_token, seeded_series):
    # New series, never approved
    sid = client.post(
        "/api/v1/series",
        json={"title": "Autre", "topic": "sujet", "kind": "documentary", "planned_episodes": 1, "language": "fr"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]
    episode_id = client.get(f"/api/v1/series/{sid}", headers={"Authorization": f"Bearer {owner_token}"}).json()["episodes"][0]["id"]
    r = client.post(f"/api/v1/publishing/episodes/{episode_id}", headers={"Authorization": f"Bearer {owner_token}"})
    # Episode not produced/approved -> 409 (no content without explicit validation)
    assert r.status_code == 409


def test_licensing_blocks_unknown_license(client, owner_token):
    from app.core.db import SessionLocal
    from app.models import LicenceRecord, Series

    # Produce + approve a fresh series
    sid = client.post(
        "/api/v1/series",
        json={"title": "Licence", "topic": "sujet", "kind": "documentary", "planned_episodes": 1, "language": "fr"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]
    client.post(
        f"/api/v1/series/{sid}/run",
        json={"series_id": sid, "dry_run": False},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    episode_id = client.get(f"/api/v1/series/{sid}", headers={"Authorization": f"Bearer {owner_token}"}).json()["episodes"][0]["id"]
    client.post(
        f"/api/v1/review/episodes/{episode_id}/decide",
        json={"status": "approved", "comment": "ok"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    # Inject a blocking licence record
    db = SessionLocal()
    db.add(LicenceRecord(series_id=sid, asset_ref="risky-audio", kind="music", origin="unknown",
                         license="unknown", usage="pub", source_url="", risk="block"))
    db.commit()
    db.close()

    # Publish blocked by licensing agent
    r = client.post(f"/api/v1/publishing/episodes/{episode_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 409
    assert "licence" in r.json()["detail"].lower()
