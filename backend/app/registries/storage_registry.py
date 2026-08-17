from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from typing import Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import decrypt_secret, encrypt_secret
from app.models import Asset, StorageBackend

settings = get_settings()

STORAGE_ROOT = os.path.join(settings.data_dir, "storage")


class StorageAdapter(ABC):
    @abstractmethod
    def upload(self, path: str, data: bytes, content_type: str = "") -> str:
        """Return remote path/key."""

    @abstractmethod
    def download(self, path: str) -> bytes:
        ...

    @abstractmethod
    def signed_url(self, path: str, expires: int = 3600) -> str:
        ...

    @abstractmethod
    def delete(self, path: str) -> None:
        ...

    @abstractmethod
    def healthcheck(self) -> bool:
        ...


class LocalStorageAdapter(StorageAdapter):
    def __init__(self, root: str | None = None):
        self.root = root or STORAGE_ROOT

    def _abs(self, path: str) -> str:
        path = path.lstrip("/")
        abs_path = os.path.abspath(os.path.join(self.root, path))
        root_abs = os.path.abspath(self.root)
        if not abs_path.startswith(root_abs):
            raise ValueError("Path traversal blocked")
        return abs_path

    def upload(self, path: str, data: bytes, content_type: str = "") -> str:
        abs_path = self._abs(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(data)
        return path

    def download(self, path: str) -> bytes:
        with open(self._abs(path), "rb") as f:
            return f.read()

    def signed_url(self, path: str, expires: int = 3600) -> str:
        return f"file://{self._abs(path)}?expires={int(time.time()) + expires}"

    def delete(self, path: str) -> None:
        abs_path = self._abs(path)
        if os.path.exists(abs_path):
            os.remove(abs_path)

    def healthcheck(self) -> bool:
        os.makedirs(self.root, exist_ok=True)
        return True


class S3CompatibleAdapter(StorageAdapter):
    """S3, R2, B2, MinIO via boto3 with a configurable endpoint."""

    def __init__(self, config: dict):
        import boto3

        self.bucket = config.get("bucket", "video-factory")
        self.client = boto3.client(
            "s3",
            endpoint_url=config.get("endpoint_url"),
            region_name=config.get("region", "us-east-1"),
            aws_access_key_id=config.get("access_key"),
            aws_secret_access_key=config.get("secret_key"),
        )

    def upload(self, path: str, data: bytes, content_type: str = "") -> str:
        extra = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=path, Body=data, **extra)
        return path

    def download(self, path: str) -> bytes:
        resp = self.client.get_object(Bucket=self.bucket, Key=path)
        return resp["Body"].read()

    def signed_url(self, path: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": path}, ExpiresIn=expires
        )

    def delete(self, path: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=path)

    def healthcheck(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False


class SupabaseStorageAdapter(StorageAdapter):
    def __init__(self, config: dict):
        self.url = config.get("url") or settings.supabase_url
        self.key = config.get("service_role_key") or settings.supabase_service_role_key
        self.bucket = config.get("bucket", "assets")

    def upload(self, path: str, data: bytes, content_type: str = "") -> str:
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}"}
        if content_type:
            headers["Content-Type"] = content_type
        resp = httpx.post(
            f"{self.url}/storage/v1/object/{self.bucket}/{path}",
            content=data, headers=headers, timeout=60,
        )
        resp.raise_for_status()
        return path

    def download(self, path: str) -> bytes:
        resp = httpx.get(
            f"{self.url}/storage/v1/object/{self.bucket}/{path}",
            headers={"Authorization": f"Bearer {self.key}"}, timeout=60,
        )
        resp.raise_for_status()
        return resp.content

    def signed_url(self, path: str, expires: int = 3600) -> str:
        resp = httpx.post(
            f"{self.url}/storage/v1/object/sign/{self.bucket}/{path}",
            json={"expiresIn": expires},
            headers={"apikey": self.key, "Authorization": f"Bearer {self.key}"},
            timeout=30,
        )
        resp.raise_for_status()
        return f"{self.url}/storage/v1{resp.json()['signedURL']}"

    def delete(self, path: str) -> None:
        httpx.delete(
            f"{self.url}/storage/v1/object/{self.bucket}/{path}",
            headers={"apikey": self.key, "Authorization": f"Bearer {self.key}"}, timeout=30,
        )

    def healthcheck(self) -> bool:
        try:
            resp = httpx.get(
                f"{self.url}/storage/v1/bucket",
                headers={"apikey": self.key, "Authorization": f"Bearer {self.key}"}, timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False


def build_adapter(storage: StorageBackend) -> StorageAdapter:
    config = json.loads(decrypt_secret(storage.config_encrypted) or "{}")
    if storage.kind == "local":
        return LocalStorageAdapter(root=config.get("root"))
    if storage.kind == "nas":
        return LocalStorageAdapter(root=config.get("root") or "/mnt/nas")
    if storage.kind in ("s3", "r2", "b2", "minio"):
        return S3CompatibleAdapter(config)
    if storage.kind == "supabase":
        return SupabaseStorageAdapter(config)
    if storage.kind == "pcloud":
        raise HTTPException(501, "pCloud adapter requires pCloud SDK (configured separately)")
    raise HTTPException(400, f"Unknown storage kind: {storage.kind}")


class StorageRegistry:
    def __init__(self, db: Session, workspace_id: int):
        self.db = db
        self.workspace_id = workspace_id

    def list(self) -> list[StorageBackend]:
        return list(
            self.db.scalars(
                select(StorageBackend)
                .where(StorageBackend.workspace_id == self.workspace_id)
                .order_by(StorageBackend.priority)
            )
        )

    def get(self, storage_id: int) -> StorageBackend:
        s = self.db.get(StorageBackend, storage_id)
        if not s or s.workspace_id != self.workspace_id:
            raise HTTPException(404, "Storage backend not found")
        return s

    def create(self, data) -> StorageBackend:
        if data.kind not in ("local", "pcloud", "supabase", "s3", "r2", "b2", "minio", "nas"):
            raise HTTPException(400, f"Invalid storage kind: {data.kind}")
        s = StorageBackend(
            workspace_id=self.workspace_id,
            name=data.name,
            kind=data.kind,
            config_encrypted=encrypt_secret(json.dumps(data.config)) if data.config else "",
            priority=data.priority,
            quota_bytes=data.quota_bytes,
            cost_per_gb=data.cost_per_gb,
            status=data.status,
            region=data.region,
            replication=data.replication,
        )
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def update(self, storage_id: int, data) -> StorageBackend:
        s = self.get(storage_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "config":
                if value:
                    s.config_encrypted = encrypt_secret(json.dumps(value))
            else:
                setattr(s, field, value)
        self.db.commit()
        self.db.refresh(s)
        return s

    def delete(self, storage_id: int) -> None:
        s = self.get(storage_id)
        self.db.delete(s)
        self.db.commit()

    def healthcheck(self, storage_id: int) -> dict:
        s = self.get(storage_id)
        try:
            ok = build_adapter(s).healthcheck()
        except Exception:
            ok = False
        s.healthy = ok
        s.last_healthcheck_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.db.commit()
        return {"id": s.id, "name": s.name, "healthy": ok}

    def select_active(self) -> list[StorageBackend]:
        actives = [s for s in self.list() if s.status == "active"]
        actives.sort(key=lambda s: s.priority)
        return actives or [self.create_default_local()]

    def create_default_local(self) -> StorageBackend:
        local = next((s for s in self.list() if s.kind == "local"), None)
        if local:
            return local
        return self.create(StorageCreateShim("Local", "local", {}, 0, 0.0, "active", "", ""))

    def store_asset(self, path: str, data: bytes, kind: str = "file", content_type: str = "", replicas: int | None = None) -> list[Asset]:
        backends = self.select_active()
        if replicas is None:
            replicas = len(backends)
        checksum = hashlib.sha256(data).hexdigest()
        stored: list[Asset] = []
        for i, backend in enumerate(backends[: max(replicas, 1)]):
            adapter = build_adapter(backend)
            remote_path = adapter.upload(f"{path}", data, content_type)
            backend.used_bytes += len(data)
            asset = Asset(
                workspace_id=self.workspace_id,
                storage_id=backend.id,
                path=remote_path,
                checksum=checksum,
                size=len(data),
                kind=kind,
                content_type=content_type,
            )
            self.db.add(asset)
            stored.append(asset)
        self.db.commit()
        for a in stored:
            self.db.refresh(a)
        return stored

    def read_asset(self, asset: Asset) -> bytes:
        backend = self.get(asset.storage_id)
        return build_adapter(backend).download(asset.path)

    def signed_url_for(self, asset: Asset, expires: int = 3600) -> str:
        backend = self.get(asset.storage_id)
        return build_adapter(backend).signed_url(asset.path, expires)


class StorageCreateShim:
    """Small shim to allow default-local creation from code."""

    def __init__(self, name, kind, config, priority, cost, status, region, replication):
        self.name = name
        self.kind = kind
        self.config = config
        self.priority = priority
        self.quota_bytes = 0
        self.cost_per_gb = cost
        self.status = status
        self.region = region
        self.replication = replication
