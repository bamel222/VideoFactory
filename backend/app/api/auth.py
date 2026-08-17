from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.audit import audit_log
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, Workspace
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.registries.provider_registry import seed_fake_providers
from app.registries.storage_registry import StorageRegistry

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    exists = db.scalar(select(func.count(User.id)).select_from(User))
    if exists and not request.headers.get("x-bootstrap-token"):
        raise HTTPException(403, "Registration closed. Ask an Owner to create your account.")
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "Email already registered")

    role = "owner" if not exists else body.role
    ws = Workspace(name=f"Workspace {body.name}")
    db.add(ws)
    db.flush()

    user = User(
        email=body.email.lower(),
        name=body.name,
        hashed_password=hash_password(body.password),
        role=role,
        workspace_id=ws.id,
    )
    db.add(user)
    db.flush()
    if role == "owner":
        ws.owner_id = user.id

    seed_fake_providers(db, ws.id)
    StorageRegistry(db, ws.id).create_default_local()
    db.commit()

    audit_log(db, user.id, "auth.register", "user", user.id, {"role": role}, request.client.host if request.client else None)
    token = create_access_token(user.id, user.email, user.role, user.workspace_id)
    return TokenResponse(access_token=token, role=user.role, email=user.email, user_id=user.id, workspace_id=user.workspace_id)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    if not user.active:
        raise HTTPException(403, "Account disabled")
    audit_log(db, user.id, "auth.login", "user", user.id, {}, request.client.host if request.client else None)
    token = create_access_token(user.id, user.email, user.role, user.workspace_id)
    return TokenResponse(access_token=token, role=user.role, email=user.email, user_id=user.id, workspace_id=user.workspace_id)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
