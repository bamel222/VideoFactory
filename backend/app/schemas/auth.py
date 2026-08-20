from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    user_id: int
    workspace_id: int
    password_expired: bool = False


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str
    role: str = "reviewer"


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: str = "reviewer"


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    active: bool | None = None
    password: str | None = None


class UserOut(ORMModel):
    id: int
    email: str
    name: str
    role: str
    active: bool


class NotificationProfile(BaseModel):
    """Self-service notification credentials. Set a field to update it; an
    empty string clears it."""

    notification_email: str | None = None
    discord_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
