from __future__ import annotations

import base64
import datetime as dt
import hashlib

import pytest
from cryptography.fernet import Fernet


STRONG_PW = "Str0ng-Passw0rd-2026!"
STRONG_PW_2 = "N3w-Str0ng-Passw0rd-2027!"


def _create_user(client, owner_token, email, password=STRONG_PW):
    r = client.post(
        "/api/v1/users",
        json={"email": email, "name": email.split("@")[0], "password": password, "role": "reviewer"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_weak_password_rejected_on_user_create(client, owner_token):
    r = client.post(
        "/api/v1/users",
        json={"email": "weak@vf.ai", "name": "Weak", "password": "abc", "role": "reviewer"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "WEAK_PASSWORD"


def test_weak_password_rejected_on_register(client):
    r = client.post("/api/v1/auth/register", json={"email": "weak2@vf.ai", "name": "Weak", "password": "short"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "WEAK_PASSWORD"


def test_change_password_full_flow(client, owner_token):
    _create_user(client, owner_token, "pwflow@vf.ai")
    r = _login(client, "pwflow@vf.ai", STRONG_PW)
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert r.json()["password_expired"] is False

    # Wrong old password
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "wrong", "new_password": STRONG_PW_2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "WRONG_PASSWORD"

    # Valid change
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": STRONG_PW, "new_password": STRONG_PW_2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    # Old password no longer works, new one does
    assert _login(client, "pwflow@vf.ai", STRONG_PW).status_code == 401
    assert _login(client, "pwflow@vf.ai", STRONG_PW_2).status_code == 200

    # Reuse of a previously used password is rejected
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": STRONG_PW_2, "new_password": STRONG_PW},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "PASSWORD_REUSED"


def test_login_reports_password_expired(client, owner_token, monkeypatch):
    import app.core.password_policy as pp
    from app.core.db import SessionLocal
    from app.models import User

    _create_user(client, owner_token, "expired@vf.ai")

    db = SessionLocal()
    user = db.query(User).filter(User.email == "expired@vf.ai").first()
    user.password_changed_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=100)
    db.commit()
    db.close()

    monkeypatch.setattr(pp.settings, "password_max_age_days", 90)
    r = _login(client, "expired@vf.ai", STRONG_PW)
    assert r.status_code == 200
    assert r.json()["password_expired"] is True

    # After rotation the flag clears
    token = r.json()["access_token"]
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": STRONG_PW, "new_password": STRONG_PW_2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    r = _login(client, "expired@vf.ai", STRONG_PW_2)
    assert r.status_code == 200
    assert r.json()["password_expired"] is False


def test_login_lockout_after_failures(client):
    for i in range(5):
        r = _login(client, "owner@vf.ai", "wrong-password")
        assert r.status_code == 401
    r = _login(client, "owner@vf.ai", "password123")
    assert r.status_code == 423


def test_login_rate_limit(client, owner_token):
    from app.core import redis as redis_store

    redis_store._client.flushall()
    _create_user(client, owner_token, "ratelimit@vf.ai")
    for _ in range(10):
        assert _login(client, "ratelimit@vf.ai", STRONG_PW).status_code == 200
    r = _login(client, "ratelimit@vf.ai", STRONG_PW)
    assert r.status_code == 429


def test_ssrf_unit_validation():
    from app.core.ssrf import validate_ssrf_safe

    validate_ssrf_safe("https://8.8.8.8/")
    with pytest.raises(ValueError):
        validate_ssrf_safe("http://10.0.0.1/")
    with pytest.raises(ValueError):
        validate_ssrf_safe("http://169.254.169.254/latest/meta-data")
    with pytest.raises(ValueError):
        validate_ssrf_safe("http://127.0.0.1:3001/")
    with pytest.raises(ValueError):
        validate_ssrf_safe("http://[::1]/")
    with pytest.raises(ValueError):
        validate_ssrf_safe("ftp://example.com/x")
    with pytest.raises(ValueError):
        validate_ssrf_safe("http://")


def test_provider_endpoint_ssrf_blocked(client, owner_token):
    for ep in ["http://10.0.0.5", "http://169.254.169.254/latest/meta-data", "http://127.0.0.1:3001/x"]:
        r = client.post(
            "/api/v1/providers",
            json={"name": "Evil", "role": "tts", "endpoint": ep},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert r.status_code == 400, ep
    r = client.post(
        "/api/v1/providers",
        json={"name": "Ok", "role": "tts", "endpoint": "mock://tts"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200


def _png_bytes(size=64) -> bytes:
    """Minimal valid PNG generated in pure python (1x1 RGBA)."""
    raw = b""
    row = b"\x00" + bytes([255, 0, 0, 255]) * 1
    import struct
    import zlib

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    raw = chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(row)) + chunk(b"IEND", b"")
    return b"\x89PNG\r\n\x1a\n" + raw


def test_upload_valid_png_accepted(client, reviewer_token):
    r = client.post(
        "/api/v1/storage/upload",
        files={"file": ("pixel.png", _png_bytes(), "image/png")},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["asset_id"]


def test_upload_corrupt_png_rejected(client, reviewer_token):
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00" * 512
    r = client.post(
        "/api/v1/storage/upload",
        files={"file": ("broken.png", payload, "image/png")},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert r.status_code == 400


def test_upload_magic_mismatch_rejected(client, reviewer_token):
    r = client.post(
        "/api/v1/storage/upload",
        files={"file": ("fake.png", b"this is actually text", "image/png")},
        headers={"Authorization": f"Bearer {reviewer_token}"},
    )
    assert r.status_code == 400


def test_multikey_rotation(client, monkeypatch):
    import app.core.encryption as enc
    from app.core.encryption import decrypt_secret, encrypt_secret

    key_a = Fernet.generate_key()
    key_b = Fernet.generate_key()
    legacy = [Fernet(key_a)]
    rotated = [Fernet(key_b), Fernet(key_a)]

    monkeypatch.setattr(enc, "_FERNETS", legacy)
    token = encrypt_secret("secret-v1")

    # Rotated stack can still decrypt the old token; new tokens use key B.
    monkeypatch.setattr(enc, "_FERNETS", rotated)
    assert decrypt_secret(token) == "secret-v1"
    new_token = encrypt_secret("secret-v2")
    assert decrypt_secret(new_token) == "secret-v2"
    assert Fernet(key_a).decrypt(token.encode()).decode() == "secret-v1"
    assert Fernet(key_b).decrypt(new_token.encode()).decode() == "secret-v2"

    # Legacy key dropped -> old tokens no longer decryptable.
    monkeypatch.setattr(enc, "_FERNETS", [Fernet(key_b)])
    assert decrypt_secret(token) == ""


def test_provider_create_update_endpoint_ssrf(client, owner_token):
    r = client.post(
        "/api/v1/providers",
        json={"name": "Evil2", "role": "video", "endpoint": "http://192.168.1.10"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 400

    r = client.post(
        "/api/v1/providers",
        json={"name": "Ok2", "role": "video", "endpoint": "mock://video"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    pid = r.json()["id"]

    r = client.patch(
        f"/api/v1/providers/{pid}",
        json={"endpoint": "http://169.254.169.254/latest/meta-data"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 400
