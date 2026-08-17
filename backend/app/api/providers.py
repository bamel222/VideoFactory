from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_owner
from app.core.audit import audit_log
from app.core.security import require_permission
from app.models import User
from app.registries.provider_registry import ProviderRegistry
from app.schemas.provider import ProviderCreate, ProviderUpdate

router = APIRouter(prefix="/providers", tags=["providers"])


def _registry(db: Session, user: User) -> ProviderRegistry:
    return ProviderRegistry(db, user.workspace_id)


@router.get("")
def list_providers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_registry(db, user).serialize(p) for p in _registry(db, user).list()]


@router.post("")
def create_provider(
    body: ProviderCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not require_permission(user.role, "providers.manage"):
        raise HTTPException(403, "Owner or Admin only")
    p = _registry(db, user).create(body)
    audit_log(db, user.id, "provider.create", "provider", p.id, {"name": p.name, "role": p.role}, request.client.host if request.client else None)
    return _registry(db, user).serialize(p, with_key=False)


@router.patch("/{provider_id}")
def update_provider(
    provider_id: int,
    body: ProviderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not require_permission(user.role, "providers.manage"):
        raise HTTPException(403, "Owner or Admin only")
    p = _registry(db, user).update(provider_id, body)
    audit_log(db, user.id, "provider.update", "provider", p.id, {"name": p.name}, request.client.host if request.client else None)
    return _registry(db, user).serialize(p, with_key=False)


@router.delete("/{provider_id}")
def delete_provider(
    provider_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_owner),
):
    p = _registry(db, user).get(provider_id)
    audit_log(db, user.id, "provider.delete", "provider", p.id, {"name": p.name}, request.client.host if request.client else None)
    _registry(db, user).delete(provider_id)
    return {"ok": True}


@router.post("/{provider_id}/healthcheck")
def healthcheck_provider(provider_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _registry(db, user).healthcheck(provider_id)


@router.post("/{provider_id}/test-key")
def test_key(provider_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _registry(db, user).test_api_key(provider_id)
