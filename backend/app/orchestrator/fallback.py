from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from app.registries.provider_registry import ProviderRegistry

T = TypeVar("T")


def select_provider_with_fallback(registry: ProviderRegistry, role: str, requirements: dict | None = None):
    return registry.select(role, requirements)


def execute_with_fallback(
    registry: ProviderRegistry,
    role: str,
    requirements: dict | None,
    fn: Callable[[object], T],
) -> tuple[T, object]:
    """Run fn against each candidate provider in priority order until one succeeds."""
    candidates = [
        p for p in registry.list()
        if p.role == role and p.status == "active"
    ]
    if requirements and requirements.get("language"):
        candidates = [p for p in candidates if not p.languages or requirements["language"] in p.languages]
    candidates.sort(key=lambda p: (p.priority, -p.quality_estimate))

    if not candidates:
        raise RuntimeError(f"No active provider for role '{role}'")

    last_error: Exception | None = None
    for provider in candidates:
        try:
            result = fn(provider)
            return result, provider
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    raise RuntimeError(f"All providers for role '{role}' failed. Last error: {last_error}")
