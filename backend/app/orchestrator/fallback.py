from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from app.registries.provider_registry import ProviderRegistry

T = TypeVar("T")


def execute_with_fallback(
    registry: ProviderRegistry,
    role: str,
    requirements: dict | None,
    fn: Callable[[object], T],
) -> tuple[T, object]:
    """Run fn against each candidate provider in priority order until one succeeds.

    Mirrors ProviderRegistry.select (healthy + language + format filtering) but
    iterates over every candidate so a failing provider triggers the next one.
    """
    requirements = requirements or {}
    candidates = [
        p for p in registry.list()
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
    candidates.sort(key=lambda p: (p.priority, -(p.quality_estimate or 0)))

    if not candidates:
        raise RuntimeError(f"No active provider for role '{role}'")

    last_error: Exception | None = None
    for provider in candidates:
        remaining = provider.quota_total - provider.quota_used
        if remaining <= 0 and provider.quota_total != 0:
            continue
        try:
            result = fn(provider)
            return result, provider
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    raise RuntimeError(f"All providers for role '{role}' failed. Last error: {last_error}")
