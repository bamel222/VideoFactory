from __future__ import annotations

import pytest


def test_provider_crud_and_fallback(client, owner_token):
    # Create two TTS providers: primary (priority 5) and backup (priority 50)
    p1 = client.post(
        "/api/v1/providers",
        json={"name": "TTS Primaire", "role": "tts", "endpoint": "mock://tts", "priority": 5, "quality_estimate": 90},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]
    p2 = client.post(
        "/api/v1/providers",
        json={"name": "TTS Backup", "role": "tts", "endpoint": "mock://tts", "priority": 50, "quality_estimate": 60},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()["id"]

    # Disable the primary
    r = client.patch(
        f"/api/v1/providers/{p1}",
        json={"status": "disabled"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.json()["status"] == "disabled"

    # Selection must fall back to the next active TTS provider (Fake TTS, priority 10)
    from app.core.db import SessionLocal
    from app.registries.provider_registry import ProviderRegistry

    db = SessionLocal()
    registry = ProviderRegistry(db, 1)
    selected = registry.select("tts")
    db.close()
    assert selected is not None
    assert selected.status == "active"
    assert selected.priority == 10  # the default fake, not the disabled primary

    # Healthcheck + test key
    r = client.post(f"/api/v1/providers/{p2}/healthcheck", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.json()["healthy"] is True
    r = client.post(f"/api/v1/providers/{p2}/test-key", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.json()["ok"] is True

    # Secret must be masked in API output
    created = client.post(
        "/api/v1/providers",
        json={"name": "Secret Provider", "role": "research", "api_key": "sk-abcd1234", "endpoint": "mock://research"},
        headers={"Authorization": f"Bearer {owner_token}"},
    ).json()
    assert "sk-abcd1234" not in str(created)


def test_storage_multi_backend(client, owner_token):
    # Create a second active backend
    r = client.post(
        "/api/v1/storage",
        json={"name": "Backup", "kind": "nas", "config": {"root": "./data/storage2"}, "priority": 20},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text

    # Upload stores the asset on all active backends
    up = client.post(
        "/api/v1/storage/upload",
        files={"file": ("demo.txt", b"hello video factory", "text/plain")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert up.status_code == 200, up.text
    asset_id = up.json()["asset_id"]

    # Download via common interface
    dl = client.get(f"/api/v1/storage/assets/{asset_id}/download", headers={"Authorization": f"Bearer {owner_token}"})
    import base64

    assert base64.b64decode(dl.json()["data_b64"]) == b"hello video factory"

    # Signed URL
    su = client.get(f"/api/v1/storage/assets/{asset_id}/signed-url", headers={"Authorization": f"Bearer {owner_token}"})
    assert "expires" in su.json()["url"]

    # Both storage backends recorded assets for the same path
    from app.core.db import SessionLocal
    from app.models import Asset

    db = SessionLocal()
    assets = db.query(Asset).filter(Asset.path == "upload/1/demo.txt").all()
    db.close()
    assert len(assets) >= 2
