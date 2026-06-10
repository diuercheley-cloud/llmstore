from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from app.core.time import utc_now
from app.models.commercial.commercial_model_lifecycle import (
    CommercialModelLifecycleRecord,
    CommercialModelRollbackRecord,
)
from app.models.commercial.commercial_model_supply_chain import CommercialSignedModelRegistryEntry
from app.services.models.model_lifecycle_manager import (
    _canonical_json,
    _log_audit,
    _sanitize_text,
    _validate_transition,
)
from app.services.models.model_lineage import create_lineage_entry
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

QUARANTINE_REASONS = {
    "checksum_mismatch",
    "signature_invalid",
    "provenance_invalid",
    "crl_revoked",
    "policy_violation",
    "manual_quarantine",
    "attestation_failure",
    "lineage_broken",
    "sovereign_violation",
    "runtime_drift",
}


async def quarantine_lifecycle_model(
    db: AsyncSession,
    lifecycle_record_id: UUID,
    *,
    reason: str,
    quarantined_by: str | None = None,
    cluster_id: str | None = None,
    node_id: str | None = None,
) -> CommercialModelLifecycleRecord:
    if reason not in QUARANTINE_REASONS:
        raise ValueError(f"Invalid quarantine reason: {reason}")
    record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    if not record:
        raise ValueError("Lifecycle record not found")
    if not _validate_transition(record.lifecycle_state, "quarantined"):
        raise ValueError(f"Cannot quarantine model in state: {record.lifecycle_state}")
    record.previous_lifecycle_state = record.lifecycle_state
    record.lifecycle_state = "quarantined"
    record.state_changed_at = utc_now()
    record.updated_at = utc_now()
    if record.registry_entry_id:
        entry = await db.get(CommercialSignedModelRegistryEntry, record.registry_entry_id)
        if entry and entry.trust_state != "quarantined":
            entry.trust_state = "quarantined"
            entry.updated_at = utc_now()
    await db.flush()
    await _log_audit(
        db,
        action="model_lifecycle_quarantined",
        status="success",
        payload={"lifecycle_record_id": str(lifecycle_record_id), "model_name": record.model_name, "reason": reason},
        result={"quarantined_by": quarantined_by, "previous_state": record.previous_lifecycle_state},
    )
    return record


async def release_from_quarantine(
    db: AsyncSession,
    lifecycle_record_id: UUID,
    *,
    released_by: str | None = None,
    target_state: str = "staged",
    reason: str | None = None,
) -> CommercialModelLifecycleRecord:
    record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    if not record:
        raise ValueError("Lifecycle record not found")
    if record.lifecycle_state != "quarantined":
        raise ValueError(f"Model is not quarantined, current state: {record.lifecycle_state}")
    if not _validate_transition("quarantined", target_state):
        raise ValueError(f"Invalid transition from quarantined to {target_state}")
    record.previous_lifecycle_state = record.lifecycle_state
    record.lifecycle_state = target_state
    record.state_changed_at = utc_now()
    record.updated_at = utc_now()
    if record.registry_entry_id:
        entry = await db.get(CommercialSignedModelRegistryEntry, record.registry_entry_id)
        if entry and entry.trust_state == "quarantined":
            entry.trust_state = "pending"
            entry.updated_at = utc_now()
    await db.flush()
    await _log_audit(
        db,
        action="model_quarantine_released",
        status="success",
        payload={"lifecycle_record_id": str(lifecycle_record_id), "model_name": record.model_name},
        result={"released_by": released_by, "target_state": target_state, "reason": reason},
    )
    return record


async def rollback_model(
    db: AsyncSession,
    lifecycle_record_id: UUID,
    *,
    rollback_to_state: str = "staged",
    rollback_reason: str,
    rolled_back_by: str | None = None,
    promotion_request_id: UUID | None = None,
    predecessor_checksum: str | None = None,
    chain_of_custody_json: dict[str, Any] | None = None,
) -> CommercialModelRollbackRecord:
    record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    if not record:
        raise ValueError("Lifecycle record not found")
    if not _validate_transition(record.lifecycle_state, "rolled_back"):
        raise ValueError(f"Cannot rollback from state: {record.lifecycle_state}")
    if not _validate_transition("rolled_back", rollback_to_state):
        raise ValueError(f"Invalid rollback target state: {rollback_to_state}")
    from_state = record.lifecycle_state
    record.previous_lifecycle_state = from_state
    record.lifecycle_state = "rolled_back"
    record.state_changed_at = utc_now()
    record.updated_at = utc_now()
    verification_payload = {
        "lifecycle_record_id": str(lifecycle_record_id),
        "from_state": from_state,
        "to_state": rollback_to_state,
        "predecessor_checksum": predecessor_checksum,
        "rolled_back_by": _sanitize_text(rolled_back_by) or "admin",
        "rolled_back_at": utc_now().isoformat(),
    }
    verification_hash = hashlib.sha256(
        _canonical_json(sanitize_report_payload(verification_payload)).encode("utf-8")
    ).hexdigest()
    checksum_verified = False
    if predecessor_checksum and record.checksum_sha256:
        checksum_verified = predecessor_checksum == record.checksum_sha256
    sanitized_chain = sanitize_report_payload(chain_of_custody_json) if chain_of_custody_json else None
    rollback = CommercialModelRollbackRecord(
        lifecycle_record_id=lifecycle_record_id,
        promotion_request_id=promotion_request_id,
        rollback_from_state=from_state,
        rollback_to_state=rollback_to_state,
        rollback_reason=_sanitize_text(rollback_reason, max_length=1000) or "manual rollback",
        rolled_back_by=_sanitize_text(rolled_back_by),
        verification_hash=verification_hash,
        predecessor_checksum=predecessor_checksum,
        checksum_verified=checksum_verified,
        lineage_valid=record.lineage_validated,
        attestation_valid=record.attestation_bound,
        chain_of_custody_json=sanitized_chain,
    )
    db.add(rollback)
    await db.flush()
    receipt_payload = {
        "rollback_id": str(rollback.id),
        "lifecycle_record_id": str(lifecycle_record_id),
        "from_state": from_state,
        "to_state": rollback_to_state,
        "verification_hash": verification_hash,
        "checksum_verified": checksum_verified,
    }
    rollback.immutable_receipt_hash = hashlib.sha256(
        _canonical_json(sanitize_report_payload(receipt_payload)).encode("utf-8")
    ).hexdigest()
    record.lifecycle_state = rollback_to_state
    record.state_changed_at = utc_now()
    record.updated_at = utc_now()
    if record.registry_entry_id:
        entry = await db.get(CommercialSignedModelRegistryEntry, record.registry_entry_id)
        if entry and entry.trust_state in ("quarantined", "revoked"):
            entry.trust_state = "pending"
            entry.updated_at = utc_now()
    await db.flush()
    if record.lineage_validated:
        await create_lineage_entry(
            db,
            lifecycle_record_id=lifecycle_record_id,
            source_type="rollback",
            derivation_method="rollback_restoration",
            artifact_hash=verification_hash,
            predecessor_hash=predecessor_checksum,
            evidence_json={"rollback_reason": rollback_reason, "from_state": from_state},
        )
    await _log_audit(
        db,
        action="model_lifecycle_rollback",
        status="success",
        payload={"lifecycle_record_id": str(lifecycle_record_id), "model_name": record.model_name},
        result={
            "from_state": from_state,
            "to_state": rollback_to_state,
            "verification_hash": verification_hash,
            "rollback_id": str(rollback.id),
        },
    )
    return rollback


async def list_quarantined_models(
    db: AsyncSession,
    *,
    limit: int = 100,
) -> list[CommercialModelLifecycleRecord]:
    stmt = (
        select(CommercialModelLifecycleRecord)
        .where(CommercialModelLifecycleRecord.lifecycle_state == "quarantined")
        .order_by(desc(CommercialModelLifecycleRecord.state_changed_at))
        .limit(min(max(limit, 1), 500))
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def list_rollback_records(
    db: AsyncSession,
    *,
    lifecycle_record_id: UUID | None = None,
    limit: int = 100,
) -> list[CommercialModelRollbackRecord]:
    stmt = select(CommercialModelRollbackRecord).order_by(desc(CommercialModelRollbackRecord.created_at))
    if lifecycle_record_id:
        stmt = stmt.where(CommercialModelRollbackRecord.lifecycle_record_id == lifecycle_record_id)
    stmt = stmt.limit(min(max(limit, 1), 500))
    result = await db.execute(stmt)
    return result.scalars().all()


def serialize_rollback_record(
    rollback: CommercialModelRollbackRecord,
    *,
    sensitive: bool = False,
) -> dict[str, Any]:
    def _short(value: str | None) -> str | None:
        if not value:
            return None
        return value if sensitive else value[:12]

    return sanitize_report_payload({
        "id": str(rollback.id),
        "lifecycle_record_id": str(rollback.lifecycle_record_id),
        "promotion_request_id": str(rollback.promotion_request_id) if rollback.promotion_request_id else None,
        "rollback_from_state": rollback.rollback_from_state,
        "rollback_to_state": rollback.rollback_to_state,
        "rollback_reason": rollback.rollback_reason,
        "rolled_back_by": rollback.rolled_back_by,
        "verification_hash": _short(rollback.verification_hash),
        "predecessor_checksum": _short(rollback.predecessor_checksum),
        "checksum_verified": rollback.checksum_verified,
        "lineage_valid": rollback.lineage_valid,
        "attestation_valid": rollback.attestation_valid,
        "immutable_receipt_hash": _short(rollback.immutable_receipt_hash),
        "created_at": rollback.created_at.isoformat(),
    })
