from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_owner
from app.core.audit import audit_log
from app.core.password_policy import enforce_password_policy, password_is_reused, record_password
from app.core.security import hash_password
from app.models import User
from app.schemas.auth import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_owner)):
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("", response_model=UserOut)
def create_user(body: UserCreate, request: Request, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "Email already exists")
    if body.role not in ("owner", "admin", "reviewer"):
        raise HTTPException(400, "Invalid role")
    enforce_password_policy(body.password)
    user = User(
        email=body.email.lower(),
        name=body.name,
        hashed_password=hash_password(body.password),
        role=body.role,
        workspace_id=owner.workspace_id,
    )
    db.add(user)
    db.flush()
    record_password(db, user, user.hashed_password)
    db.commit()
    db.refresh(user)
    audit_log(db, owner.id, "user.create", "user", user.id, {"role": body.role}, request.client.host if request.client else None)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == owner.id and body.active is False:
        raise HTTPException(400, "Cannot deactivate yourself")
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if field == "password":
            enforce_password_policy(value)
            if password_is_reused(db, user, value):
                raise HTTPException(400, "Password has been used recently; choose a different one")
            user.hashed_password = hash_password(value)
            record_password(db, user, user.hashed_password)
        else:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    audit_log(db, owner.id, "user.update", "user", user.id, body.model_dump(exclude_unset=True), request.client.host if request.client else None)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == owner.id:
        raise HTTPException(400, "Cannot delete yourself")
    user.active = False
    db.commit()
    audit_log(db, owner.id, "user.delete", "user", user.id, {}, request.client.host if request.client else None)
    return {"ok": True, "message": "User deactivated (soft delete)"}
