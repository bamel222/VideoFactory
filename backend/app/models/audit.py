from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_id: Mapped[str] = mapped_column(String(100), index=True, nullable=True)
    details_json: Mapped[str] = mapped_column(default="")
    ip: Mapped[str] = mapped_column(String(100), default="")
    user_agent: Mapped[str] = mapped_column(String(500), default="")
