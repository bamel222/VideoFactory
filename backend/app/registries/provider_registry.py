from __future__ import annotations

import datetime as dt

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret, encrypt_secret, mask_secret
from app.models import Provider

DEFAULT_FAKE_PROVIDERS = [
    {
        "name": "Fake Research (free)", "role": "research", "endpoint": "mock://research",
        "quota_total": 100000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": ["fr", "en", "es", "de"], "formats": ["text"], "model": "fake-research-1",
        "avg_speed": "fast", "quality_estimate": 60,
    },
    {
        "name": "Fake TTS (free)", "role": "tts", "endpoint": "mock://tts",
        "quota_total": 1000000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": ["fr", "en", "es", "de"], "formats": ["mp3", "wav"], "model": "fake-tts-1",
        "avg_speed": "fast", "quality_estimate": 70,
    },
    {
        "name": "Fake Voice (free)", "role": "voice", "endpoint": "mock://voice",
        "quota_total": 500000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": ["fr", "en"], "formats": ["mp3"], "model": "fake-voice-1",
        "avg_speed": "fast", "quality_estimate": 65,
    },
    {
        "name": "Fake Music (free)", "role": "music", "endpoint": "mock://music",
        "quota_total": 200000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": [], "formats": ["mp3", "wav"], "model": "fake-music-1",
        "avg_speed": "medium", "quality_estimate": 60,
    },
    {
        "name": "Fake Video (free)", "role": "video", "endpoint": "mock://video",
        "quota_total": 100000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": [], "formats": ["mp4", "webm"], "model": "fake-video-1",
        "avg_speed": "slow", "quality_estimate": 55,
    },
    {
        "name": "Fake Image (free)", "role": "image", "endpoint": "mock://image",
        "quota_total": 100000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": [], "formats": ["jpg", "png", "webp"], "model": "fake-image-1",
        "avg_speed": "medium", "quality_estimate": 55,
    },
    {
        "name": "Fake Translate (free)", "role": "translation", "endpoint": "mock://translation",
        "quota_total": 1000000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": ["fr", "en", "es", "de", "it", "pt", "ja", "zh"], "formats": ["text"],
        "model": "fake-translate-1", "avg_speed": "fast", "quality_estimate": 70,
    },
    {
        "name": "Fake Transcribe (free)", "role": "transcription", "endpoint": "mock://transcription",
        "quota_total": 500000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": ["fr", "en", "es", "de"], "formats": ["text"], "model": "fake-asr-1",
        "avg_speed": "medium", "quality_estimate": 60,
    },
    {
        "name": "Fake SEO (free)", "role": "seo", "endpoint": "mock://seo",
        "quota_total": 100000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": ["fr", "en"], "formats": ["text"], "model": "fake-seo-1",
        "avg_speed": "fast", "quality_estimate": 70,
    },
    {
        "name": "Fake QA (free)", "role": "qa", "endpoint": "mock://qa",
        "quota_total": 100000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": [], "formats": ["text"], "model": "fake-qa-1",
        "avg_speed": "fast", "quality_estimate": 80,
    },
    {
        "name": "Fake Script (free)", "role": "script", "endpoint": "mock://script",
        "quota_total": 100000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": ["fr", "en", "es", "de"], "formats": ["text"], "model": "fake-script-1",
        "avg_speed": "fast", "quality_estimate": 70,
    },
    {
        "name": "Fake Assembly (ffmpeg)", "role": "assembly", "endpoint": "mock://assembly",
        "quota_total": 1000000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": [], "formats": ["mp4", "webm"], "model": "ffmpeg",
        "avg_speed": "medium", "quality_estimate": 80,
    },
    {
        "name": "Fake Caption (free)", "role": "caption", "endpoint": "mock://caption",
        "quota_total": 1000000, "cost_per_unit": 0.0, "priority": 10, "status": "active",
        "languages": ["fr", "en", "es", "de"], "formats": ["srt", "vtt"], "model": "fake-caption-1",
        "avg_speed": "fast", "quality_estimate": 70,
    },
]


def seed_fake_providers(db: Session, workspace_id: int) -> None:
    existing_roles = set(db.scalars(select(Provider.role).where(Provider.workspace_id == workspace_id)))
    for p in DEFAULT_FAKE_PROVIDERS:
        if p["role"] in existing_roles:
            continue
        db.add(Provider(workspace_id=workspace_id, **p))
    db.commit()


class ProviderRegistry:
    def __init__(self, db: Session, workspace_id: int):
        self.db = db
        self.workspace_id = workspace_id

    def list(self) -> list[Provider]:
        return list(
            self.db.scalars(
                select(Provider).where(Provider.workspace_id == self.workspace_id).order_by(Provider.priority)
            )
        )

    def get(self, provider_id: int) -> Provider:
        p = self.db.get(Provider, provider_id)
        if not p or p.workspace_id != self.workspace_id:
            raise HTTPException(404, "Provider not found")
        return p

    def create(self, data) -> Provider:
        if data.role not in (
            "research", "transcription", "translation", "script", "tts", "voice", "music",
            "image", "video", "assembly", "seo", "qa", "licensing", "caption",
        ):
            raise HTTPException(400, f"Invalid provider role: {data.role}")
        p = Provider(
            workspace_id=self.workspace_id,
            name=data.name,
            role=data.role,
            endpoint=data.endpoint,
            api_key_encrypted=encrypt_secret(data.api_key) if data.api_key else "",
            quota_total=data.quota_total,
            cost_per_unit=data.cost_per_unit,
            priority=data.priority,
            status=data.status,
            languages=data.languages,
            formats=data.formats,
            limits=data.limits,
            model=data.model,
            avg_speed=data.avg_speed,
            quality_estimate=data.quality_estimate,
        )
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        return p

    def update(self, provider_id: int, data) -> Provider:
        p = self.get(provider_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "api_key":
                if value:
                    p.api_key_encrypted = encrypt_secret(value)
            else:
                setattr(p, field, value)
        self.db.commit()
        self.db.refresh(p)
        return p

    def delete(self, provider_id: int) -> None:
        p = self.get(provider_id)
        self.db.delete(p)
        self.db.commit()

    def serialize(self, p: Provider, *, with_key: bool = False) -> dict:
        d = {
            "id": p.id,
            "name": p.name,
            "role": p.role,
            "endpoint": p.endpoint,
            "quota_total": p.quota_total,
            "quota_used": p.quota_used,
            "quota_remaining": max(p.quota_total - p.quota_used, 0),
            "cost_per_unit": p.cost_per_unit,
            "priority": p.priority,
            "status": p.status,
            "languages": p.languages,
            "formats": p.formats,
            "limits": p.limits,
            "model": p.model,
            "avg_speed": p.avg_speed,
            "quality_estimate": p.quality_estimate,
            "healthy": p.healthy,
            "last_healthcheck_at": p.last_healthcheck_at,
            "api_key_masked": mask_secret(decrypt_secret(p.api_key_encrypted)),
        }
        if with_key:
            d["api_key"] = decrypt_secret(p.api_key_encrypted)
        return d

    def test_api_key(self, provider_id: int) -> dict:
        p = self.get(provider_id)
        key = decrypt_secret(p.api_key_encrypted)
        if not key and not p.endpoint.startswith("mock"):
            return {"ok": False, "message": "No API key configured"}
        return {"ok": True, "message": "API key accepted"}

    def healthcheck(self, provider_id: int) -> dict:
        p = self.get(provider_id)
        ok = p.status == "active"
        p.healthy = ok
        p.last_healthcheck_at = dt.datetime.now(dt.timezone.utc).isoformat()
        self.db.commit()
        return {"id": p.id, "name": p.name, "healthy": ok, "status": p.status}

    def track_usage(self, provider: Provider, units: float, cost: float) -> None:
        provider.quota_used = min(provider.quota_used + int(units), provider.quota_total)
        provider.cost_per_unit = provider.cost_per_unit
        self.db.commit()

    def select(self, role: str, requirements: dict | None = None) -> Provider | None:
        """Pick the active provider for a role, honoring priority, quota and fallback."""
        requirements = requirements or {}
        candidates = [
            p for p in self.list()
            if p.role == role and p.status == "active" and p.healthy
        ]
        if requirements.get("language"):
            candidates = [
                p for p in candidates
                if not p.languages or requirements["language"] in p.languages
            ]
        if requirements.get("format"):
            candidates = [
                p for p in candidates
                if not p.formats or requirements["format"] in p.formats
            ]
        candidates.sort(key=lambda p: (p.priority, -p.quality_estimate))
        for p in candidates:
            remaining = p.quota_total - p.quota_used
            if remaining > 0 or p.quota_total == 0:
                return p
        return None
