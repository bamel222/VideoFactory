from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import tempfile
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

# Streaming chunk size (1 MB).
CHUNK_SIZE = 1024 * 1024


class StorageAdapter(ABC):
    @abstractmethod
    def upload_stream(self, path: str, src, content_type: str = "") -> str:
        """Stream `src` (a binary file-like) to storage; return remote path/key."""

    def upload(self, path: str, data: bytes, content_type: str = "") -> str:
        """Convenience: upload in-memory bytes via a stream."""
        return self.upload_stream(path, io.BytesIO(data), content_type)

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
        # Compare canonical common path (not a string prefix) to block traversal.
        try:
            common = os.path.commonpath([root_abs, abs_path])
        except ValueError:
            raise ValueError("Path traversal blocked")
        if common != root_abs:
            raise ValueError("Path traversal blocked")
        return abs_path

    def upload_stream(self, path: str, src, content_type: str = "") -> str:
        abs_path = self._abs(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            shutil.copyfileobj(src, f, length=CHUNK_SIZE)
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
        # Verify the root exists AND is writable (not just that makedirs works).
        os.makedirs(self.root, exist_ok=True)
        probe = os.path.join(self.root, ".vf_probe")
        try:
            with open(probe, "wb") as f:
                f.write(b"ok")
            os.remove(probe)
            return True
        except OSError:
            return False


class S3CompatibleAdapter(StorageAdapter):
    """S3, R2, B2, MinIO, OVHCloud via boto3 with a configurable endpoint."""

    def __init__(self, config: dict):
        import boto3
        from botocore.config import Config as BotoConfig

        self.bucket = config.get("bucket", "video-factory")
        # Path-style addressing: required by single-endpoint S3 providers
        # (OVHcloud, MinIO, Backblaze B2, Cloudflare R2) where the endpoint is
        # not bucket-specific.
        # verify_ssl=False allows self-signed TLS (common with self-hosted MinIO).
        self.client = boto3.client(
            "s3",
            endpoint_url=config.get("endpoint_url"),
            region_name=config.get("region", "us-east-1"),
            aws_access_key_id=config.get("access_key"),
            aws_secret_access_key=config.get("secret_key"),
            verify=config.get("verify_ssl", True),
            config=BotoConfig(s3={"addressing_style": "path"}),
        )

    def upload_stream(self, path: str, src, content_type: str = "") -> str:
        extra = {"ContentType": content_type} if content_type else {}
        self.client.upload_fileobj(src, self.bucket, path, ExtraArgs=extra)
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
        # Raises on failure (registry captures the message); returns True on success.
        self.client.head_bucket(Bucket=self.bucket)
        return True


class SupabaseStorageAdapter(StorageAdapter):
    def __init__(self, config: dict):
        self.url = (config.get("url") or settings.supabase_url or "").rstrip("/")
        self.key = config.get("service_role_key") or settings.supabase_service_role_key
        self.bucket = config.get("bucket", "assets")

    def upload_stream(self, path: str, src, content_type: str = "") -> str:
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}"}
        if content_type:
            headers["Content-Type"] = content_type

        def _chunks():
            while True:
                chunk = src.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

        resp = httpx.post(
            f"{self.url}/storage/v1/object/{self.bucket}/{path}",
            content=_chunks(), headers=headers, timeout=60,
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
        # Supabase returns a RELATIVE path (e.g. "/object/sign/bucket/key?token=…").
        signed = (resp.json() or {}).get("signedURL") or (resp.json() or {}).get("url") or ""
        if not signed:
            raise RuntimeError("Supabase did not return a signed URL")
        if signed.startswith("http"):
            return signed
        return f"{self.url}/storage/v1{signed}"

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


class PCloudStorageAdapter(StorageAdapter):
    """pCloud via its REST API (OAuth2 access token, no SDK required).

    Config: {"api_endpoint": "https://api.pcloud.com", "access_token": "...",
             "root": "/video-factory"}  (api_endpoint = eapi.pcloud.com for EU)
    """

    def __init__(self, config: dict):
        self.endpoint = (config.get("api_endpoint") or "https://api.pcloud.com").rstrip("/")
        self.access_token = config.get("access_token") or config.get("oauth_token") or ""
        self.root = (config.get("root") or "/video-factory").strip("/")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        resp = httpx.request(
            method, f"{self.endpoint}{path}", headers=self._headers(), timeout=120, **kwargs
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") != 0:
            raise RuntimeError(f"pCloud error: {data.get('error')}")
        return data

    def _remote_path(self, path: str) -> str:
        clean = "/".join(p for p in path.strip("/").split("/") if p)
        return f"/{self.root}/{clean}"

    def _ensure_folders(self, remote_path: str) -> None:
        # uploadfile does NOT auto-create parents; create them top-down.
        parts = remote_path.strip("/").split("/")[:-1]  # drop the filename
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else f"/{part}"
            self._request("POST", "/createfolderifnotexists", params={"path": current})

    def upload_stream(self, path: str, src, content_type: str = "") -> str:
        remote = self._remote_path(path)
        self._ensure_folders(remote)
        self._request("POST", "/uploadfile", params={"path": remote}, content=src)
        return path

    def download(self, path: str) -> bytes:
        link = self._request("GET", "/getfilelink", params={"path": self._remote_path(path)})
        hosts = link.get("hosts") or []
        if not hosts:
            raise RuntimeError("pCloud: no download host returned")
        resp = httpx.get(f"https://{hosts[0]}{link['path']}", timeout=120)
        resp.raise_for_status()
        return resp.content

    def signed_url(self, path: str, expires: int = 3600) -> str:
        # pCloud getfilelink returns a short-lived direct link (expiry is
        # provider-controlled; the `expires` arg is accepted for interface parity).
        link = self._request("GET", "/getfilelink", params={"path": self._remote_path(path)})
        hosts = link.get("hosts") or []
        if not hosts:
            raise RuntimeError("pCloud: no download host returned")
        return f"https://{hosts[0]}{link['path']}"

    def delete(self, path: str) -> None:
        self._request("GET", "/deletefile", params={"path": self._remote_path(path)})

    def healthcheck(self) -> bool:
        self._request("GET", "/userinfo")
        return True


def build_adapter(storage: StorageBackend) -> StorageAdapter:
    config = json.loads(decrypt_secret(storage.config_encrypted) or "{}")
    _validate_storage_config(storage.kind, config)
    if storage.kind == "nas":
        return LocalStorageAdapter(root=config.get("root") or "/mnt/nas")
    if storage.kind in ("s3", "r2", "b2", "minio"):
        return S3CompatibleAdapter(config)
    if storage.kind == "supabase":
        return SupabaseStorageAdapter(config)
    if storage.kind == "pcloud":
        return PCloudStorageAdapter(config)
    raise HTTPException(400, f"Unknown storage kind: {storage.kind}")


def _open_source(src) -> tuple[object, bool]:
    """Normalize a source (bytes / path / file-like) into a seekable file-like.

    Returns (fileobj, should_close). Non-seekable file-likes are spooled to a
    temporary file so size/checksum can be measured and the payload re-streamed.
    """
    if isinstance(src, (bytes, bytearray)):
        return io.BytesIO(src), False
    if isinstance(src, (str, os.PathLike)):
        return open(src, "rb"), True
    if hasattr(src, "read"):
        try:
            if src.seekable():
                src.seek(0)
                return src, False
        except (AttributeError, OSError):
            pass
        spool = tempfile.SpooledTemporaryFile(max_size=CHUNK_SIZE)
        shutil.copyfileobj(src, spool, length=CHUNK_SIZE)
        spool.seek(0)
        return spool, True
    raise TypeError(f"Type de source non supporté: {type(src)!r}")


def _measure_stream(src) -> tuple[int, str]:
    """Return (size, sha256 hexdigest) of a seekable stream, rewinding it."""
    h = hashlib.sha256()
    size = 0
    while True:
        chunk = src.read(CHUNK_SIZE)
        if not chunk:
            break
        size += len(chunk)
        h.update(chunk)
    src.seek(0)
    return size, h.hexdigest()


def _validate_storage_config(kind: str, config: dict) -> None:
    """SSRF-guard outbound storage endpoints (Supabase URL, S3/MinIO endpoint).

    Skipped when settings.allow_private_storage_endpoints is enabled (e.g. a
    local MinIO instance). Endpoints without an http(s) scheme are ignored.
    """
    from app.core.ssrf import validate_ssrf_safe

    if settings.allow_private_storage_endpoints:
        return

    urls: list[str] = []
    if kind == "supabase":
        urls.append(config.get("url") or settings.supabase_url)
    elif kind in ("s3", "r2", "b2", "minio"):
        urls.append(config.get("endpoint_url"))
    elif kind == "pcloud":
        urls.append(config.get("api_endpoint"))

    for u in urls:
        if not u:
            continue
        if not u.startswith(("http://", "https://")):
            continue
        try:
            validate_ssrf_safe(u)
        except ValueError as exc:
            raise HTTPException(400, f"Endpoint de stockage invalide (SSRF): {exc}")


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
        if data.kind not in ("pcloud", "supabase", "s3", "r2", "b2", "minio", "nas"):
            raise HTTPException(400, f"Invalid storage kind: {data.kind}")
        # Validate the endpoint/config up front (SSRF guard) so a bad config
        # fails at creation time with a clear error instead of a silent "ko".
        _validate_storage_config(data.kind, data.config or {})
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
        # Remove the backend's assets first (they hold a FK to it), attempting to
        # delete the underlying objects too; then drop the backend row.
        from app.models import Asset

        assets = list(self.db.scalars(select(Asset).where(Asset.storage_id == storage_id)))
        for asset in assets:
            try:
                build_adapter(s).delete(asset.path)
            except Exception:  # noqa: BLE001
                pass  # object may already be gone; the row is still removed
            self.db.delete(asset)
        self.db.delete(s)
        self.db.commit()

    def healthcheck(self, storage_id: int) -> dict:
        s = self.get(storage_id)
        error: str | None = None
        try:
            ok = build_adapter(s).healthcheck()
        except Exception as exc:  # noqa: BLE001
            ok = False
            error = str(exc)[:400]
        s.healthy = ok
        s.last_healthcheck_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.db.commit()
        return {"id": s.id, "name": s.name, "healthy": ok, "error": error}

    def select_active(self) -> list[StorageBackend]:
        actives = [s for s in self.list() if s.status == "active"]
        actives.sort(key=lambda s: s.priority)
        return actives

    def store_asset(self, path: str, data: bytes, kind: str = "file", content_type: str = "", replicas: int | None = None) -> list[Asset]:
        """Upload in-memory bytes (convenience wrapper around the streaming path)."""
        return self.store_asset_stream(path, data, kind=kind, content_type=content_type, replicas=replicas)

    def store_asset_stream(self, path: str, src, *, kind: str = "file", content_type: str = "", replicas: int | None = None) -> list[Asset]:
        """Stream an asset from `src` (bytes, filesystem path, or file-like) to storage.

        The payload is never fully buffered in memory: size and checksum are
        computed in a single streaming pass, then the source is streamed to each
        backend (local disk, S3 upload_fileobj, Supabase chunked upload).
        """
        backends = self.select_active()
        if replicas is None:
            replicas = len(backends)
        if not backends:
            raise HTTPException(500, "Aucun backend de stockage actif")

        src_file, should_close = _open_source(src)
        try:
            size, checksum = _measure_stream(src_file)
            stored: list[Asset] = []
            for i, backend in enumerate(backends[: max(replicas, 1)]):
                # Enforce the backend quota before uploading (0 == unlimited).
                if backend.quota_bytes and backend.used_bytes + size > backend.quota_bytes:
                    raise HTTPException(
                        507,
                        f"Quota de stockage dépassé sur '{backend.name}' "
                        f"({backend.used_bytes + size}/{backend.quota_bytes} octets)",
                    )
                adapter = build_adapter(backend)
                src_file.seek(0)
                remote_path = adapter.upload_stream(f"{path}", src_file, content_type)
                backend.used_bytes += size
                asset = Asset(
                    workspace_id=self.workspace_id,
                    storage_id=backend.id,
                    path=remote_path,
                    checksum=checksum,
                    size=size,
                    kind=kind,
                    content_type=content_type,
                )
                self.db.add(asset)
                stored.append(asset)
            self.db.commit()
            for a in stored:
                self.db.refresh(a)
            return stored
        finally:
            if should_close:
                src_file.close()

    def read_asset(self, asset: Asset) -> bytes:
        backend = self.get(asset.storage_id)
        return build_adapter(backend).download(asset.path)

    def signed_url_for(self, asset: Asset, expires: int = 3600) -> str:
        backend = self.get(asset.storage_id)
        return build_adapter(backend).signed_url(asset.path, expires)
