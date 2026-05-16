"""Governance-related advisory invariants."""

from __future__ import annotations

from typing import Any

from app.services.invariants.base import InvariantResult, _as_mapping, advisory_result


def validate_dry_run_does_not_mutate_persistent_state(operation: dict[str, Any] | None) -> InvariantResult:
    """Dry-run governance decisions must stay non-mutating."""

    payload = _as_mapping(operation)
    dry_run = bool(payload.get("dry_run"))
    mutations = payload.get("persistent_mutations") or ()
    state_changed = bool(payload.get("persistent_state_changed"))
    passed = (not dry_run) or (not mutations and not state_changed)
    return advisory_result(
        name="dry_run_does_not_mutate_persistent_state",
        passed=passed,
        message="dry_run must not mutate persistent state",
        details={
            "dry_run": dry_run,
            "persistent_mutation_count": len(tuple(mutations)),
            "persistent_state_changed": state_changed,
        },
    )
