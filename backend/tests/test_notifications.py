from __future__ import annotations


def test_notification_profile_roundtrip(client, owner_token):
    # Initially nothing configured.
    p = client.get("/api/v1/notifications/profile", headers={"Authorization": f"Bearer {owner_token}"})
    assert p.status_code == 200, p.text
    assert p.json()["discord_configured"] is False
    assert p.json()["telegram_configured"] is False

    # Configure Discord + Telegram (encrypted at rest).
    r = client.put(
        "/api/v1/notifications/profile",
        json={
            "discord_webhook_url": "https://discord.com/api/webhooks/123/abc",
            "telegram_bot_token": "123456:ABC-DEF",
            "telegram_chat_id": "42",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["discord_configured"] is True
    assert r.json()["telegram_configured"] is True

    # Secrets must never leak through the API.
    body = r.text
    assert "123456:ABC-DEF" not in body
    assert "https://discord.com" not in body


def test_notification_profile_clearing(client, owner_token):
    client.put(
        "/api/v1/notifications/profile",
        json={"discord_webhook_url": "https://discord.com/api/webhooks/x/y"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    r = client.put(
        "/api/v1/notifications/profile",
        json={"discord_webhook_url": ""},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.json()["discord_configured"] is False


def test_pipeline_runs_without_blocking_on_notifications(client, owner_token, seeded_series):
    """Notifications are fire-and-forget: running with notify_email=True but no
    email provider configured must still complete the pipeline."""
    from app.core.db import SessionLocal
    from app.models import Series

    # Set notify flags on the series directly (simulating a launch-time choice).
    db = SessionLocal()
    s = db.get(Series, seeded_series)
    s.notify_email = True
    s.notify_discord = True
    s.notify_telegram = True
    db.commit()
    db.close()

    r = client.post(
        f"/api/v1/series/{seeded_series}/run",
        json={"series_id": seeded_series, "dry_run": False, "notify": {"email": True, "discord": True, "telegram": True}},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    # Pipeline completed despite no email provider / webhooks being configured.
    assert r.json()["status"] in ("done", "failed")
    assert r.json()["total_tasks"] > 0


def test_secondary_notification_email(client, owner_token):
    # Set a secondary email.
    r = client.put(
        "/api/v1/notifications/profile",
        json={"notification_email": "Backup@Example.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["notification_email"] == "backup@example.com"

    # Clear it.
    r = client.put(
        "/api/v1/notifications/profile",
        json={"notification_email": ""},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.json()["notification_email"] == ""

    # Invalid value rejected.
    r = client.put(
        "/api/v1/notifications/profile",
        json={"notification_email": "not-an-email"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 400


def test_cleanup_removes_intermediates(client, owner_token, seeded_series):
    """After a successful run, intermediate media files are deleted while the
    final video asset (final_assembly) is kept."""
    from app.core.db import SessionLocal
    from app.models import Asset, Checkpoint, JobTask, Series

    r = client.post(
        f"/api/v1/series/{seeded_series}/run",
        json={"series_id": seeded_series, "dry_run": False},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "done"

    db = SessionLocal()
    try:
        s = db.get(Series, seeded_series)
        # Final assembly assets must still exist.
        final_assets = (
            db.query(Asset)
            .join(JobTask, JobTask.checkpoint_id.isnot(None))
            .filter(JobTask.series_id == seeded_series, JobTask.task_type == "final_assembly")
            .all()
        )
        # Intermediate task types must no longer have their files/asset rows.
        for tt in ("image_generate", "video_generate", "tts_voice", "music_generate", "clip_assembly"):
            cps = (
                db.query(Checkpoint)
                .join(JobTask, Checkpoint.task_id == JobTask.id)
                .filter(JobTask.series_id == seeded_series, JobTask.task_type == tt)
                .all()
            )
            for cp in cps:
                if cp.content_ref:
                    # The stored asset must have been removed.
                    remaining = db.query(Asset).filter(Asset.path == cp.content_ref).count()
                    assert remaining == 0, f"intermediate asset not cleaned for {tt}"
    finally:
        db.close()


def test_series_stores_notify_prefs(client, owner_token):
    r = client.post(
        "/api/v1/series",
        json={
            "title": "Série notifiée",
            "topic": "test",
            "kind": "documentary",
            "planned_episodes": 1,
            "language": "fr",
            "notify": {"email": True, "discord": False, "telegram": True},
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["notify_email"] is True
    assert body["notify_discord"] is False
    assert body["notify_telegram"] is True
