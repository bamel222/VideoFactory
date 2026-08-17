from __future__ import annotations

import pytest


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "Strict-Transport-Security" in r.headers
    assert "Content-Security-Policy" in r.headers
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]


def test_login_bad_credentials(client):
    r = client.post("/api/v1/auth/login", json={"email": "owner@vf.ai", "password": "wrong"})
    assert r.status_code == 401


def test_login_ok(client):
    r = client.post("/api/v1/auth/login", json={"email": "reviewer@vf.ai", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["role"] == "reviewer"


def test_protected_route_requires_token(client):
    r = client.get("/api/v1/providers")
    assert r.status_code == 401


def test_rbac_reviewer_cannot_create_provider(client, reviewer_token):
    r = client.post(
        "/api/v1/providers",
        json={"name": "X", "role": "tts", "endpoint": "mock://tts"},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert r.status_code == 403


def test_rbac_owner_can_manage_users(client, owner_token, admin_token):
    r = client.post(
        "/api/v1/users",
        json={"email": "new@vf.ai", "name": "New", "password": "password123", "role": "reviewer"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    # Admin cannot create users (roles.manage is owner-only)
    r2 = client.post(
        "/api/v1/users",
        json={"email": "other@vf.ai", "name": "Other", "password": "password123", "role": "reviewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r2.status_code == 403


def test_encryption_roundtrip():
    from app.core.encryption import decrypt_secret, encrypt_secret, mask_secret

    token = encrypt_secret("sk-super-secret")
    assert token != "sk-super-secret"
    assert decrypt_secret(token) == "sk-super-secret"
    assert "*" in mask_secret("sk-super-secret")
    assert "super-secret" not in mask_secret("sk-super-secret")
