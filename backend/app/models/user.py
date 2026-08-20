from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="reviewer", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    password_changed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Notification channel credentials (encrypted at rest, never exposed via API).
    discord_webhook_url_encrypted: Mapped[str] = mapped_column(String(2000), default="")
    telegram_bot_token_encrypted: Mapped[str] = mapped_column(String(1000), default="")
    telegram_chat_id_encrypted: Mapped[str] = mapped_column(String(255), default="")
    # Optional secondary address for notifications (in addition to `email`).
    notification_email: Mapped[str] = mapped_column(String(255), default="")


class PasswordHistory(Base, TimestampMixin):
    __tablename__ = "password_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        backref="workspace", foreign_keys="User.workspace_id"
    )
