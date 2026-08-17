from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token, require_permission
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(auth.split(" ", 1)[1])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.get(User, int(payload.get("sub")))
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="User inactive or missing")
    return user


def require_perm(permission: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if not require_permission(user.role, permission):
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' lacks permission '{permission}'")
        return user

    return _dep


require_owner = require_perm("roles.manage")
require_admin = require_perm("providers.manage")
require_reviewer = require_perm("content.read")
