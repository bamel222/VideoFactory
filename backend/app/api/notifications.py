from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.encryption import decrypt_secret, encrypt_secret
from app.models import User
from app.schemas.auth import NotificationProfile

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _profile(user: User) -> dict:
    return {
        "email": user.email,
        "discord_configured": bool(decrypt_secret(user.discord_webhook_url_encrypted)),
        "telegram_configured": bool(
            decrypt_secret(user.telegram_bot_token_encrypted)
            and decrypt_secret(user.telegram_chat_id_encrypted)
        ),
    }


@router.get("/profile")
def get_profile(user: User = Depends(get_current_user)):
    return _profile(user)


@router.put("/profile")
def update_profile(
    body: NotificationProfile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.discord_webhook_url is not None:
        user.discord_webhook_url_encrypted = (
            encrypt_secret(body.discord_webhook_url) if body.discord_webhook_url else ""
        )
    if body.telegram_bot_token is not None:
        user.telegram_bot_token_encrypted = (
            encrypt_secret(body.telegram_bot_token) if body.telegram_bot_token else ""
        )
    if body.telegram_chat_id is not None:
        user.telegram_chat_id_encrypted = (
            encrypt_secret(body.telegram_chat_id) if body.telegram_chat_id else ""
        )
    db.commit()
    db.refresh(user)
    return _profile(user)
