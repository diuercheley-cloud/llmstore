"""Runtime-related advisory invariants."""

from __future__ import annotations

from typing import Any

from app.services.invariants.base import InvariantResult, _as_mapping, advisory_result


def validate_receipt_has_immutable_hash(receipt: dict[str, Any] | None) -> InvariantResult:
    """Every receipt must expose an immutable hash or equivalent digest field."""

    payload = _as_mapping(receipt)
    immutable_hash = payload.get("immutable_hash")
    return advisory_result(
        name="receipt_has_immutable_hash",
        passed=isinstance(immutable_hash, str) and bool(immutable_hash.strip()),
        message="every receipt must have immutable_hash",
        details={"immutable_hash_present": bool(immutable_hash)},
    )


def validate_repair_operation_emits_healing_receipt(operation: dict[str, Any] | None) -> InvariantResult:
    """Repair flows must report an emitted healing receipt in advisory validation."""

    payload = _as_mapping(operation)
    emitted_events = payload.get("emitted_events") or ()
    healing_receipt = payload.get("healing_receipt") or {}
    has_event = "runtime.healing_receipt.emitted" in emitted_events
    has_receipt_hash = bool(healing_receipt.get("immutable_hash"))
    return advisory_result(
        name="repair_operation_emits_healing_receipt",
        passed=has_event and has_receipt_hash,
        message="repair operation must emit healing receipt",
        details={
            "healing_event_present": has_event,
            "healing_receipt_hash_present": has_receipt_hash,
        },
    )
