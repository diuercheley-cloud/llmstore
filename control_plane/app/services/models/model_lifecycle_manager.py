from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.admin_action_log import AdminActionLog
from app.models.commercial_model_lifecycle import (
    VALID_LIFECYCLE_STATES,
    CommercialModelLifecycleRecord,
    CommercialOfflineModelVerification,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.offline_crl import is_bundle_revoked, is_peer_revoked
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

STATE_TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"staged", "quarantined", "archived"},
    "staged": {"pending_approval", "quarantined", "archived"},
    "pending_approval": {"approved", "quarantined", "rolled_back", "archived"},
    "approved": {"promoted", "quarantined", "rolled_back", "archived"},
    "promoted": {"quarantined", "rolled_back", "archived"},
    "quarantined": {"staged", "rolled_back", "revoked", "archived"},
    "revoked": {"archived"},
    "rolled_back": {"staged", "pending_approval", "archived"},
    "archived": set(),
}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _sanitize_text(value: str | None, *, max_length: int = 255) -> str | None:
    if value is None:
        return None
    sanitized = sanitize_report_payload({"value": value}).get("value")
    if sanitized is None:
        return None
    return str(sanitized).replace("\n", " ").replace("\r", " ")[:max_length]


async def _log_audit(
    db: AsyncSession,
    *,
    action: str,
    status: str,
    payload: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
) -> None:
    db.add(
        AdminActionLog(
            action=action,
            admin_role="super_admin",
            payload_json=sanitize_report_payload(payload or {}),
            result_json=sanitize_report_payload(result or {}),
            status=status,
        )
    )
    await db.flush()


def _validate_transition(current_state: str, target_state: str) -> bool:
    allowed = STATE_TRANSITIONS.get(current_state, set())
    return target_state in allowed


async def discover_model(
    db: AsyncSession,
    *,
    model_name: str,
    model_alias: str | None = None,
    model_version: str | None = None,
    provider: str | None = None,
    checksum_sha256: str | None = None,
    manifest_hash: str | None = None,
    registry_entry_id: UUID | None = None,
    tenant_scope_json: dict[str, Any] | None = None,
    provenance_id: UUID | None = None,
    sovereign_restricted: bool = False,
    export_restricted: bool = False,
    cluster_id: str | None = None,
    node_id: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> CommercialModelLifecycleRecord:
    record = CommercialModelLifecycleRecord(
        registry_entry_id=registry_entry_id,
        model_name=_sanitize_text(model_name) or "unknown",
        model_alias=_sanitize_text(model_alias, max_length=128),
        model_version=_sanitize_text(model_version, max_length=128),
        provider=_sanitize_text(provider, max_length=128),
        checksum_sha256=checksum_sha256,
        manifest_hash=manifest_hash,
        lifecycle_state="discovered",
        tenant_scope_json=sanitize_report_payload(tenant_scope_json) if tenant_scope_json is not None else None,
        provenance_id=provenance_id,
        attestation_bound=False,
        checksum_verified=False,
        signature_verified=False,
        lineage_validated=False,
        approval_required=True,
        sovereign_restricted=sovereign_restricted,
        export_restricted=export_restricted,
        cluster_id=_sanitize_text(cluster_id, max_length=255),
        node_id=_sanitize_text(node_id, max_length=255),
        metadata_json=sanitize_report_payload(metadata_json) if metadata_json is not None else None,
        state_changed_at=utc_now(),
    )
    db.add(record)
    await db.flush()
    await _log_audit(
        db,
        action="model_lifecycle_discovered",
        status="success",
        payload={"model_name": record.model_name, "lifecycle_state": "discovered"},
        result={"lifecycle_record_id": str(record.id)},
    )
    return record


async def stage_model(
    db: AsyncSession,
    lifecycle_record_id: UUID,
    *,
    staged_by: str | None = None,
) -> CommercialModelLifecycleRecord:
    record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    if not record:
        raise ValueError("Lifecycle record not found")
    if not _validate_transition(record.lifecycle_state, "staged"):
        raise ValueError(f"Invalid transition from {record.lifecycle_state} to staged")
    record.previous_lifecycle_state = record.lifecycle_state
    record.lifecycle_state = "staged"
    record.state_changed_at = utc_now()
    record.updated_at = utc_now()
    await db.flush()
    await _log_audit(
        db,
        action="model_lifecycle_staged",
        status="success",
        payload={"lifecycle_record_id": str(record.id), "model_name": record.model_name},
        result={"lifecycle_state": "staged", "staged_by": staged_by},
    )
    return record


async def transition_lifecycle_state(
    db: AsyncSession,
    lifecycle_record_id: UUID,
    *,
    target_state: str,
    changed_by: str | None = None,
    reason: str | None = None,
) -> CommercialModelLifecycleRecord:
    if target_state not in VALID_LIFECYCLE_STATES:
        raise ValueError(f"Invalid lifecycle state: {target_state}")
    record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    if not record:
        raise ValueError("Lifecycle record not found")
    if not _validate_transition(record.lifecycle_state, target_state):
        raise ValueError(f"Invalid transition from {record.lifecycle_state} to {target_state}")
    record.previous_lifecycle_state = record.lifecycle_state
    record.lifecycle_state = target_state
    record.state_changed_at = utc_now()
    record.updated_at = utc_now()
    await db.flush()
    await _log_audit(
        db,
        action=f"model_lifecycle_{target_state}",
        status="success",
        payload={"lifecycle_record_id": str(record.id), "model_name": record.model_name, "changed_by": changed_by},
        result={"from_state": record.previous_lifecycle_state, "to_state": target_state, "reason": reason},
    )
    return record


async def enforce_lifecycle_gates(
    db: AsyncSession,
    record: CommercialModelLifecycleRecord,
    *,
    require_attestation: bool = True,
    require_approval: bool = True,
    require_lineage: bool = True,
    require_checksum: bool = True,
    require_signed_provenance: bool = True,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.commercial_model_supply_chain_enabled:
        return {"allowed": True, "mode": "disabled"}
    gates: dict[str, bool] = {}
    if require_attestation:
        gates["attestation"] = record.attestation_bound
    if require_approval:
        gates["approval"] = not record.approval_required or record.lifecycle_state in {"approved", "promoted"}
    if require_lineage:
        gates["lineage"] = record.lineage_validated
    if require_checksum:
        gates["checksum"] = record.checksum_verified
    if require_signed_provenance:
        gates["signed_provenance"] = record.signature_verified or record.provenance_id is not None
    blocked = [k for k, v in gates.items() if not v]
    return {"allowed": len(blocked) == 0, "gates": gates, "blocked": blocked}


async def verify_offline_model(
    db: AsyncSession,
    *,
    model_name: str,
    checksum_sha256: str | None = None,
    manifest_hash: str | None = None,
    lifecycle_record_id: UUID | None = None,
    verification_type: str = "offline_import",
    media_ref: str | None = None,
    media_uuid: str | None = None,
    source_cluster_id: str | None = None,
    signed_manifest: dict[str, Any] | None = None,
    verified_by: str | None = None,
) -> CommercialOfflineModelVerification:
    settings = get_settings()
    if lifecycle_record_id:
        record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    else:
        result = await db.execute(
            select(CommercialModelLifecycleRecord)
            .where(CommercialModelLifecycleRecord.model_name == model_name)
            .order_by(desc(CommercialModelLifecycleRecord.updated_at))
        )
        record = result.scalars().first()

    signature_valid = False
    checksum_valid = False
    provenance_valid = False
    crl_valid = True
    attestation_valid = False
    lineage_valid = False

    if record:
        if record.signature_verified:
            signature_valid = True
        if record.checksum_verified:
            checksum_valid = True
        if record.provenance_id:
            provenance_valid = True
        if record.attestation_bound:
            attestation_valid = True
        if record.lineage_validated:
            lineage_valid = True

    if manifest_hash and await is_bundle_revoked(db, manifest_hash):
        crl_valid = False
    if checksum_sha256 and await is_bundle_revoked(db, checksum_sha256):
        crl_valid = False
    if source_cluster_id and await is_peer_revoked(db, source_cluster_id):
        crl_valid = False

    overall_valid = signature_valid and checksum_valid and provenance_valid and crl_valid and attestation_valid and lineage_valid

    details: dict[str, Any] = {
        "signature_valid": signature_valid,
        "checksum_valid": checksum_valid,
        "provenance_valid": provenance_valid,
        "crl_valid": crl_valid,
        "attestation_valid": attestation_valid,
        "lineage_valid": lineage_valid,
    }
    verification = CommercialOfflineModelVerification(
        lifecycle_record_id=record.id if record else None,
        verification_type=verification_type,
        model_name=_sanitize_text(model_name) or "unknown",
        checksum_sha256=checksum_sha256,
        manifest_hash=manifest_hash,
        signature_valid=signature_valid,
        checksum_valid=checksum_valid,
        provenance_valid=provenance_valid,
        crl_valid=crl_valid,
        attestation_valid=attestation_valid,
        lineage_valid=lineage_valid,
        overall_valid=overall_valid,
        media_ref=_sanitize_text(media_ref, max_length=512),
        media_uuid=_sanitize_text(media_uuid, max_length=128),
        source_cluster_id=_sanitize_text(source_cluster_id, max_length=255),
        signed_manifest=sanitize_report_payload(signed_manifest) if signed_manifest else None,
        verification_details_json=sanitize_report_payload(details),
        verified_by=_sanitize_text(verified_by),
        verified_at=utc_now(),
    )
    db.add(verification)
    await db.flush()

    if record and overall_valid:
        record.checksum_verified = checksum_valid
        record.signature_verified = signature_valid
        record.lineage_validated = lineage_valid
        record.updated_at = utc_now()
        await db.flush()

    await _log_audit(
        db,
        action="offline_model_verification",
        status="success" if overall_valid else "failure",
        payload={"model_name": model_name, "verification_type": verification_type},
        result={"overall_valid": overall_valid, "details": details},
    )
    return verification


async def get_lifecycle_record(
    db: AsyncSession,
    lifecycle_record_id: UUID,
) -> CommercialModelLifecycleRecord | None:
    return await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)


async def get_lifecycle_by_model(
    db: AsyncSession,
    model_name: str,
) -> CommercialModelLifecycleRecord | None:
    result = await db.execute(
        select(CommercialModelLifecycleRecord)
        .where(CommercialModelLifecycleRecord.model_name == model_name)
        .order_by(desc(CommercialModelLifecycleRecord.updated_at))
    )
    return result.scalars().first()


async def list_lifecycle_records(
    db: AsyncSession,
    *,
    lifecycle_state: str | None = None,
    cluster_id: str | None = None,
    limit: int = 100,
) -> list[CommercialModelLifecycleRecord]:
    stmt = select(CommercialModelLifecycleRecord).order_by(desc(CommercialModelLifecycleRecord.updated_at))
    if lifecycle_state:
        stmt = stmt.where(CommercialModelLifecycleRecord.lifecycle_state == lifecycle_state)
    if cluster_id:
        stmt = stmt.where(CommercialModelLifecycleRecord.cluster_id == cluster_id)
    stmt = stmt.limit(min(max(limit, 1), 500))
    result = await db.execute(stmt)
    return result.scalars().all()


async def summarize_lifecycle_status(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(CommercialModelLifecycleRecord))
    records = result.scalars().all()
    state_counts: dict[str, int] = {}
    for record in records:
        state_counts[record.lifecycle_state] = state_counts.get(record.lifecycle_state, 0) + 1
    sovereign_count = sum(1 for r in records if r.sovereign_restricted)
    export_restricted_count = sum(1 for r in records if r.export_restricted)
    verified_count = sum(1 for r in records if r.checksum_verified and r.signature_verified and r.lineage_validated)
    return sanitize_report_payload({
        "total": len(records),
        "state_counts": state_counts,
        "sovereign_restricted": sovereign_count,
        "export_restricted": export_restricted_count,
        "fully_verified": verified_count,
        "pending_approval": state_counts.get("pending_approval", 0),
        "quarantined": state_counts.get("quarantined", 0),
    })


def serialize_lifecycle_record(
    record: CommercialModelLifecycleRecord,
    *,
    sensitive: bool = False,
) -> dict[str, Any]:
    def _short(value: str | None) -> str | None:
        if not value:
            return None
        return value if sensitive else value[:12]

    return sanitize_report_payload({
        "id": str(record.id),
        "registry_entry_id": str(record.registry_entry_id) if record.registry_entry_id else None,
        "model_name": record.model_name,
        "model_alias": record.model_alias,
        "model_version": record.model_version,
        "provider": record.provider,
        "checksum_sha256": _short(record.checksum_sha256),
        "manifest_hash": _short(record.manifest_hash),
        "lifecycle_state": record.lifecycle_state,
        "previous_lifecycle_state": record.previous_lifecycle_state,
        "provenance_id": str(record.provenance_id) if record.provenance_id else None,
        "attestation_bound": record.attestation_bound,
        "checksum_verified": record.checksum_verified,
        "signature_verified": record.signature_verified,
        "lineage_validated": record.lineage_validated,
        "approval_required": record.approval_required,
        "sovereign_restricted": record.sovereign_restricted,
        "export_restricted": record.export_restricted,
        "cluster_id": record.cluster_id,
        "node_id": record.node_id,
        "state_changed_at": record.state_changed_at.isoformat() if record.state_changed_at else None,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    })


def serialize_offline_verification(
    verification: CommercialOfflineModelVerification,
    *,
    sensitive: bool = False,
) -> dict[str, Any]:
    def _short(value: str | None) -> str | None:
        if not value:
            return None
        return value if sensitive else value[:12]

    return sanitize_report_payload({
        "id": str(verification.id),
        "lifecycle_record_id": str(verification.lifecycle_record_id) if verification.lifecycle_record_id else None,
        "verification_type": verification.verification_type,
        "model_name": verification.model_name,
        "checksum_sha256": _short(verification.checksum_sha256),
        "manifest_hash": _short(verification.manifest_hash),
        "signature_valid": verification.signature_valid,
        "checksum_valid": verification.checksum_valid,
        "provenance_valid": verification.provenance_valid,
        "crl_valid": verification.crl_valid,
        "attestation_valid": verification.attestation_valid,
        "lineage_valid": verification.lineage_valid,
        "overall_valid": verification.overall_valid,
        "media_ref": verification.media_ref,
        "media_uuid": verification.media_uuid,
        "source_cluster_id": verification.source_cluster_id,
        "verified_by": verification.verified_by,
        "verified_at": verification.verified_at.isoformat() if verification.verified_at else None,
        "created_at": verification.created_at.isoformat(),
    })
