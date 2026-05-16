"""Shared advisory primitives for platform invariants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InvariantResult:
    """Represents a deterministic advisory validation outcome."""

    name: str
    passed: bool
    severity: str
    message: str
    details: dict[str, Any]


def advisory_result(
    *,
    name: str,
    passed: bool,
    message: str,
    details: dict[str, Any] | None = None,
) -> InvariantResult:
    """Build a standard advisory result without side effects."""

    return InvariantResult(
        name=name,
        passed=passed,
        severity="advisory",
        message=message,
        details=details or {},
    )


def _as_mapping(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize optional payloads to deterministic mapping access."""

    return payload or {}

