import os
import sys
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test_vf.db"
os.environ["REDIS_URL"] = "redis://localhost:0"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-32-bytes-min!!"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["USE_FAKE_PROVIDERS"] = "true"
os.environ["MONTAGE_ENABLED"] = "false"
os.environ["DATA_DIR"] = tempfile.mkdtemp()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app.core.db import Base, engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    Base.metadata.create_all(bind=engine)
    from app.scripts.seed import run as seed_run

    seed_run()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def owner_token(client) -> str:
    r = client.post("/api/v1/auth/login", json={"email": "owner@vf.ai", "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def admin_token(client) -> str:
    r = client.post("/api/v1/auth/login", json={"email": "admin@vf.ai", "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def reviewer_token(client) -> str:
    r = client.post("/api/v1/auth/login", json={"email": "reviewer@vf.ai", "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def seeded_series(client, owner_token) -> int:
    r = client.post(
        "/api/v1/series",
        json={"title": "Série test", "topic": "les abeilles", "kind": "documentary", "planned_episodes": 1, "language": "fr"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(autouse=True)
def _fresh_redis():
    from app.core import redis as redis_store

    try:
        redis_store._client.flushall()
    except Exception:
        pass
    yield
