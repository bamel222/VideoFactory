from __future__ import annotations

from pydantic import BaseModel


class ProviderCreate(BaseModel):
    name: str
    role: str
    endpoint: str = ""
    api_key: str = ""
    quota_total: int = 0
    cost_per_unit: float = 0.0
    priority: int = 100
    status: str = "active"
    languages: list = []
    formats: list = []
    limits: dict = {}
    model: str = ""
    avg_speed: str = ""
    quality_estimate: int = 50


class ProviderUpdate(BaseModel):
    name: str | None = None
    endpoint: str | None = None
    api_key: str | None = None
    quota_total: int | None = None
    cost_per_unit: float | None = None
    priority: int | None = None
    status: str | None = None
    languages: list | None = None
    formats: list | None = None
    limits: dict | None = None
    model: str | None = None
    avg_speed: str | None = None
    quality_estimate: int | None = None


class StorageCreate(BaseModel):
    name: str
    kind: str
    config: dict = {}
    priority: int = 100
    quota_bytes: int = 0
    cost_per_gb: float = 0.0
    status: str = "active"
    region: str = ""
    replication: str = ""


class StorageUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    priority: int | None = None
    quota_bytes: int | None = None
    cost_per_gb: float | None = None
    status: str | None = None
    region: str | None = None
    replication: str | None = None
