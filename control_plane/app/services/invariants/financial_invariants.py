"""Financial and tenant-scope advisory invariants."""

from __future__ import annotations

from typing import Any

from app.services.invariants.base import InvariantResult, _as_mapping, advisory_result


def validate_tenant_scoped_record_has_client_id(record: dict[str, Any] | None) -> InvariantResult:
    """Tenant-scoped records must always carry client identity."""

    payload = _as_mapping(record)
    tenant_scoped = bool(payload.get("tenant_scoped"))
    client_id = payload.get("client_id")
    passed = (not tenant_scoped) or bool(client_id)
    return advisory_result(
        name="tenant_scoped_record_has_client_id",
        passed=passed,
        message="tenant-scoped records must include client_id",
        details={
            "tenant_scoped": tenant_scoped,
            "client_id_present": bool(client_id),
        },
    )
