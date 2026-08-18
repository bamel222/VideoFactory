from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.audit import audit_log
from app.core.login_guard import check_login_allowed, record_login_failure, reset_login_failures
from app.core.password_policy import (
    enforce_password_policy,
    password_expired,
    password_is_reused,
    record_password,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, Workspace
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.registries.provider_registry import seed_fake_providers
from app.registries.storage_registry import StorageRegistry

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    enforce_password_policy(body.password)
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
    record_password(db, user, user.hashed_password)
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
    ip = request.client.host if request.client else "unknown"
    check_login_allowed(ip, body.email)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.hashed_password):
        record_login_failure(ip, body.email)
        raise HTTPException(401, "Invalid credentials")
    if not user.active:
        raise HTTPException(403, "Account disabled")
    reset_login_failures(ip, body.email)
    audit_log(db, user.id, "auth.login", "user", user.id, {}, ip)
    token = create_access_token(user.id, user.email, user.role, user.workspace_id)
    return TokenResponse(
        access_token=token,
        role=user.role,
        email=user.email,
        user_id=user.id,
        workspace_id=user.workspace_id,
        password_expired=password_expired(user),
    )


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(400, {"code": "WRONG_PASSWORD", "message": "Mot de passe actuel incorrect"})
    if body.new_password == body.old_password:
        raise HTTPException(400, {"code": "PASSWORD_UNCHANGED", "message": "Le nouveau mot de passe doit être différent"})
    enforce_password_policy(body.new_password)
    if password_is_reused(db, user, body.new_password):
        raise HTTPException(400, {"code": "PASSWORD_REUSED", "message": "Vous avez déjà utilisé ce mot de passe récemment"})
    user.hashed_password = hash_password(body.new_password)
    record_password(db, user, user.hashed_password)
    db.commit()
    audit_log(db, user.id, "auth.change_password", "user", user.id, {}, request.client.host if request.client else None)
    return {"ok": True, "message": "Mot de passe mis à jour"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
