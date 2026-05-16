"""Sovereign export advisory invariants."""

from __future__ import annotations

from typing import Any

from app.services.invariants.base import InvariantResult, _as_mapping, advisory_result


def validate_exported_sovereign_bundle_sanitized(bundle: dict[str, Any] | None) -> InvariantResult:
    """Sovereign exports must be sanitized before leaving local trust boundaries."""

    payload = _as_mapping(bundle)
    exported = bool(payload.get("exported"))
    sanitized = bool(payload.get("sanitized"))
    leaked_fields = tuple(payload.get("unsanitized_fields") or ())
    passed = (not exported) or (sanitized and not leaked_fields)
    return advisory_result(
        name="exported_sovereign_bundle_sanitized",
        passed=passed,
        message="exported sovereign bundle must be sanitized",
        details={
            "exported": exported,
            "sanitized": sanitized,
            "unsanitized_field_count": len(leaked_fields),
        },
    )
