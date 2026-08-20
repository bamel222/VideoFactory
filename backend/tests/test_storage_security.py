from __future__ import annotations

import hashlib
import os
import tempfile

import pytest

from app.core.config import DEFAULT_SECRET_VALUES, get_settings
from app.registries.storage_registry import LocalStorageAdapter, StorageRegistry


def test_local_adapter_blocks_path_traversal():
    with tempfile.TemporaryDirectory() as root:
        adapter = LocalStorageAdapter(root=root)
        # Legitimate path inside root works.
        ok = adapter._abs("series/1/file.mp4")
        assert ok.startswith(os.path.abspath(root))
        # Traversal out of the root must be rejected.
        with pytest.raises(ValueError):
            adapter._abs("../../etc/passwd")
        # A sibling directory sharing the root prefix must also be rejected.
        sibling = root + "_evil"
        os.makedirs(sibling, exist_ok=True)
        with pytest.raises(ValueError):
            adapter._abs(os.path.join("..", os.path.basename(sibling), "x.txt"))


def test_insecure_defaults_detected():
    from app.core.config import Settings

    # Force the insecure default values regardless of the test environment.
    insecure_settings = Settings(
        ENCRYPTION_KEY=DEFAULT_SECRET_VALUES["ENCRYPTION_KEY"],
        JWT_SECRET=DEFAULT_SECRET_VALUES["JWT_SECRET"],
    )
    insecure = insecure_settings.insecure_defaults()
    assert "ENCRYPTION_KEY" in insecure
    assert "JWT_SECRET" in insecure

    # Overridden secrets are not flagged.
    secure_settings = Settings(
        ENCRYPTION_KEY="a-strong-32-byte-minimum-key-!!",
        JWT_SECRET="another-strong-secret",
    )
    assert secure_settings.insecure_defaults() == []


def test_store_asset_stream_from_path(client):
    """Streaming upload from a filesystem path: size/checksum/content correct."""
    from app.core.db import SessionLocal
    from app.models import Workspace

    payload = os.urandom(2 * 1024 * 1024)  # 2 MB of random bytes
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "big.bin")
        with open(src, "wb") as f:
            f.write(payload)

        db = SessionLocal()
        try:
            ws = db.get(Workspace, 1)
            reg = StorageRegistry(db, ws.id)
            assets = reg.store_asset_stream(
                "series/1/task_1/big.bin", src, kind="video", content_type="application/octet-stream"
            )
            assert len(assets) >= 1
            a = assets[0]
            assert a.size == len(payload)
            assert a.checksum == hashlib.sha256(payload).hexdigest()
            # Content written to disk matches the source.
            assert reg.read_asset(a) == payload
        finally:
            db.close()
