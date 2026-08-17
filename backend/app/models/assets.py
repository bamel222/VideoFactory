from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    storage_id: Mapped[int] = mapped_column(ForeignKey("storage_backends.id"), index=True, nullable=False)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(30), default="file")
    content_type: Mapped[str] = mapped_column(String(100), default="")
    public: Mapped[bool] = mapped_column(Boolean, default=False)


class LicenceRecord(Base, TimestampMixin):
    __tablename__ = "licence_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True, nullable=True)
    asset_ref: Mapped[str] = mapped_column(String(500), default="")
    kind: Mapped[str] = mapped_column(String(30), default="source")  # source|image|music|voice|video|prompt
    origin: Mapped[str] = mapped_column(String(500), default="")
    license: Mapped[str] = mapped_column(String(100), default="unknown")
    usage: Mapped[str] = mapped_column(String(500), default="")
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    risk: Mapped[str] = mapped_column(String(20), default="ok")  # ok|warn|block
    file_path: Mapped[str] = mapped_column(String(1000), default="")


class ReviewRecord(Base, TimestampMixin):
    __tablename__ = "review_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="revision")  # approved|revision|pending
    comment: Mapped[str] = mapped_column(String(2000), default="")


class SEOPackage(Base, TimestampMixin):
    __tablename__ = "seo_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="fr")
    title: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    chapters: Mapped[list] = mapped_column(JSON, default=list)
    thumbnail: Mapped[str] = mapped_column(String(1000), default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[str] = mapped_column(default="{}")


class ShortsPackage(Base, TimestampMixin):
    __tablename__ = "shorts_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default="youtube")  # youtube|tiktok|facebook
    captions: Mapped[str] = mapped_column(default="")
    cta: Mapped[str] = mapped_column(default="")
    metadata_json: Mapped[str] = mapped_column(default="{}")
    asset_path: Mapped[str] = mapped_column(String(1000), default="")


class ABTestVariant(Base, TimestampMixin):
    __tablename__ = "ab_test_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id"), index=True, nullable=False)
    field: Mapped[str] = mapped_column(String(50), default="title")  # title|hook|thumbnail
    variant: Mapped[str] = mapped_column(default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
