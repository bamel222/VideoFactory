from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.audit import audit_log
from app.core.config import get_settings
from app.core.encryption import decrypt_secret
from app.core.filevalidation import deep_validate_media, sanitize_filename, validate_file_upload
from app.core.security import require_permission
from app.models import Asset, User
from app.registries.storage_registry import StorageRegistry
from app.schemas.provider import StorageCreate, StorageUpdate

router = APIRouter(prefix="/storage", tags=["storage"])

_CHUNK_SIZE = 1024 * 1024  # 1 MB


async def _read_upload_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Stream the upload in chunks and reject early if it exceeds `max_bytes`.

    Prevents an unbounded `file.read()` from loading an arbitrarily large body
    into memory before the size limit is checked.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, "File exceeds the upload size limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _reg(db: Session, user: User) -> StorageRegistry:
    return StorageRegistry(db, user.workspace_id)


@router.get("")
def list_storage(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    out = []
    for s in _reg(db, user).list():
        d = {
            "id": s.id, "name": s.name, "kind": s.kind, "priority": s.priority,
            "quota_bytes": s.quota_bytes, "used_bytes": s.used_bytes,
            "cost_per_gb": s.cost_per_gb, "status": s.status, "region": s.region,
            "replication": s.replication, "healthy": s.healthy,
            "last_healthcheck_at": s.last_healthcheck_at,
        }
        out.append(d)
    return out


@router.post("")
def create_storage(body: StorageCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "storage.manage"):
        raise HTTPException(403, "Owner or Admin only")
    s = _reg(db, user).create(body)
    audit_log(db, user.id, "storage.create", "storage_backend", s.id, {"name": s.name, "kind": s.kind}, request.client.host if request.client else None)
    return {"id": s.id, "name": s.name, "kind": s.kind}


@router.patch("/{storage_id}")
def update_storage(storage_id: int, body: StorageUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "storage.manage"):
        raise HTTPException(403, "Owner or Admin only")
    s = _reg(db, user).update(storage_id, body)
    audit_log(db, user.id, "storage.update", "storage_backend", s.id, {}, request.client.host if request.client else None)
    return {"id": s.id, "name": s.name}


@router.delete("/{storage_id}")
def delete_storage(storage_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not require_permission(user.role, "storage.manage"):
        raise HTTPException(403, "Owner or Admin only")
    _reg(db, user).delete(storage_id)
    audit_log(db, user.id, "storage.delete", "storage_backend", storage_id, {}, request.client.host if request.client else None)
    return {"ok": True}


@router.post("/{storage_id}/healthcheck")
def healthcheck_storage(storage_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _reg(db, user).healthcheck(storage_id)


@router.post("/upload")
async def upload_asset(file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    settings = get_settings()
    filename = sanitize_filename(file.filename or "asset.bin")
    # Read with a cap applied during streaming (not after loading into RAM).
    data = await _read_upload_capped(file, settings.max_upload_mb * 1024 * 1024)
    try:
        meta = validate_file_upload(filename, data)
        deep_validate_media(data, meta["extension"])
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    rel = f"upload/{user.workspace_id}/{filename}"
    assets = _reg(db, user).store_asset(rel, data, kind="upload", content_type=file.content_type or "")
    return {"asset_id": assets[0].id, "path": assets[0].path, "checksum": assets[0].checksum, "size": assets[0].size}


@router.get("/assets")
def list_assets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        {"id": a.id, "path": a.path, "kind": a.kind, "size": a.size, "checksum": a.checksum, "storage_id": a.storage_id}
        for a in db.scalars(select(Asset).where(Asset.workspace_id == user.workspace_id).order_by(Asset.id.desc())).all()
    ]


@router.get("/assets/{asset_id}/download")
def download_asset(asset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = db.get(Asset, asset_id)
    if not asset or asset.workspace_id != user.workspace_id:
        raise HTTPException(404, "Asset not found")
    return {"data_b64": __import__("base64").b64encode(_reg(db, user).read_asset(asset)).decode()}


@router.get("/assets/{asset_id}/signed-url")
def signed_url(asset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = db.get(Asset, asset_id)
    if not asset or asset.workspace_id != user.workspace_id:
        raise HTTPException(404, "Asset not found")
    return {"url": _reg(db, user).signed_url_for(asset), "expires_in": 3600}


# NOTE: declared AFTER the /assets routes so that GET /storage/assets is not
# swallowed by the {storage_id} path parameter (which would 422 on "assets").
@router.get("/{storage_id}")
def get_storage(storage_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Return a single backend with its decrypted config (Owner/Admin only)."""
    if not require_permission(user.role, "storage.manage"):
        raise HTTPException(403, "Owner or Admin only")
    s = _reg(db, user).get(storage_id)
    try:
        config = json.loads(decrypt_secret(s.config_encrypted) or "{}")
    except Exception:
        config = {}
    return {
        "id": s.id, "name": s.name, "kind": s.kind, "priority": s.priority,
        "quota_bytes": s.quota_bytes, "used_bytes": s.used_bytes,
        "cost_per_gb": s.cost_per_gb, "status": s.status, "region": s.region,
        "replication": s.replication, "healthy": s.healthy,
        "last_healthcheck_at": s.last_healthcheck_at,
        "config": config,
    }
