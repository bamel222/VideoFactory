from __future__ import annotations

from unittest.mock import patch

import pytest

from app.registries.storage_registry import (
    PCloudStorageAdapter,
    SupabaseStorageAdapter,
    build_adapter,
)


class _FakeResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def test_supabase_signed_url_relative():
    adapter = SupabaseStorageAdapter(
        {"url": "https://xyz.supabase.co", "service_role_key": "k", "bucket": "assets"}
    )
    with patch("app.registries.storage_registry.httpx.post") as post:
        post.return_value = _FakeResp({"signedURL": "/object/sign/assets/series/1/a.mp4?token=t"})
        url = adapter.signed_url("series/1/a.mp4")
    assert url == "https://xyz.supabase.co/storage/v1/object/sign/assets/series/1/a.mp4?token=t"


def test_supabase_signed_url_absolute():
    adapter = SupabaseStorageAdapter(
        {"url": "https://xyz.supabase.co/", "service_role_key": "k", "bucket": "assets"}
    )
    with patch("app.registries.storage_registry.httpx.post") as post:
        post.return_value = _FakeResp({"signedURL": "https://full.url/x"})
        url = adapter.signed_url("series/1/a.mp4")
    assert url == "https://full.url/x"


def test_pcloud_remote_path_and_folders():
    adapter = PCloudStorageAdapter({"access_token": "t", "root": "/video-factory"})
    assert adapter._remote_path("series/1/task_1/img.png") == "/video-factory/series/1/task_1/img.png"

    created = []
    with patch.object(adapter, "_request", side_effect=lambda m, p, **kw: created.append(kw.get("params", {}).get("path"))):
        adapter._ensure_folders("/video-factory/series/1/task_1/img.png")
    assert created == ["/video-factory", "/video-factory/series", "/video-factory/series/1", "/video-factory/series/1/task_1"]


def test_pcloud_download_url():
    adapter = PCloudStorageAdapter({"access_token": "t", "root": "/vf"})
    with patch.object(adapter, "_request", return_value={"hosts": ["p-1.pcloud.com"], "path": "/dL/file.mp4"}):
        with patch("app.registries.storage_registry.httpx.get") as get:
            get.return_value = _FakeResp({}, 200)
            get.return_value.content = b"data"
            assert adapter.download("series/1/f.mp4") == b"data"
            get.assert_called_once_with("https://p-1.pcloud.com/dL/file.mp4", timeout=120)


def test_pcloud_healthcheck_checks_result_code():
    adapter = PCloudStorageAdapter({"access_token": "t"})
    with patch.object(adapter, "_request", side_effect=RuntimeError("pCloud error: bad auth")):
        with pytest.raises(RuntimeError):
            adapter.healthcheck()


def test_build_adapter_routes_kinds():
    from app.models import StorageBackend

    for kind in ("s3", "r2", "b2", "minio"):
        b = StorageBackend(name="x", kind=kind, config_encrypted="")
        with patch("app.registries.storage_registry.S3CompatibleAdapter") as cls:
            build_adapter(b)
            cls.assert_called_once()
