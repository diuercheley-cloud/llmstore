from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_model_lifecycle import (
    CommercialModelLifecycleRecord,
    CommercialModelPromotionRequest,
)
from app.services.models.model_lifecycle_manager import (
    _canonical_json,
    _log_audit,
    _sanitize_text,
    _validate_transition,
)
from app.services.models.model_provenance import (
    create_provenance_attestation,
    validate_chain_of_custody,
)
from app.services.models.signed_model_registry import sign_model_manifest, verify_model_signature
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.offline_crl import is_bundle_revoked, is_peer_revoked
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

PROMOTION_REQUEST_TYPES = {
    "staged_to_pending",
    "pending_to_approved",
    "approved_to_promoted",
    "offline_import",
    "rollback_promotion",
}


async def create_promotion_request(
    db: AsyncSession,
    *,
    lifecycle_record_id: UUID,
    request_type: str,
    requested_by: str | None = None,
    target_state: str,
    source_state: str | None = None,
    approval_count_required: int = 1,
    reason: str | None = None,
    bundle_id: UUID | None = None,
    media_ref: str | None = None,
    chain_of_custody_json: dict[str, Any] | None = None,
) -> CommercialModelPromotionRequest:
    if request_type not in PROMOTION_REQUEST_TYPES:
        raise ValueError(f"Invalid promotion request type: {request_type}")
    record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    if not record:
        raise ValueError("Lifecycle record not found")
    resolved_source = source_state or record.lifecycle_state
    if not _validate_transition(resolved_source, target_state):
        raise ValueError(f"Invalid promotion transition from {resolved_source} to {target_state}")
    sanitized_chain = (
        sanitize_report_payload(chain_of_custody_json) if chain_of_custody_json else None
    )
    if sanitized_chain:
        chain_check = await validate_chain_of_custody(sanitized_chain)
        if not chain_check["valid"]:
            raise ValueError(f"Invalid chain of custody: {chain_check['reason']}")
    request = CommercialModelPromotionRequest(
        lifecycle_record_id=lifecycle_record_id,
        request_type=request_type,
        requested_by=_sanitize_text(requested_by),
        target_state=target_state,
        source_state=resolved_source,
        approval_count_required=max(approval_count_required, 1),
        approval_count_received=0,
        status="pending",
        reason=_sanitize_text(reason, max_length=1000),
        bundle_id=bundle_id,
        media_ref=_sanitize_text(media_ref, max_length=512),
        chain_of_custody_json=sanitized_chain,
    )
    db.add(request)
    await db.flush()
    await _log_audit(
        db,
        action="promotion_request_created",
        status="success",
        payload={
            "lifecycle_record_id": str(lifecycle_record_id),
            "request_type": request_type,
            "target_state": target_state,
        },
        result={"promotion_request_id": str(request.id), "status": "pending"},
    )
    return request


async def approve_promotion_request(
    db: AsyncSession,
    promotion_request_id: UUID,
    *,
    approved_by: str | None = None,
    approval_note: str | None = None,
) -> CommercialModelPromotionRequest:
    request = await db.get(CommercialModelPromotionRequest, promotion_request_id)
    if not request:
        raise ValueError("Promotion request not found")
    if request.status != "pending":
        raise ValueError(f"Cannot approve request in status: {request.status}")
    approvals = request.approval_json or {"approvals": []}
    if not isinstance(approvals, dict):
        approvals = {"approvals": []}
    approval_list = approvals.get("approvals", [])
    approval_list.append(
        {
            "approved_by": _sanitize_text(approved_by) or "admin",
            "approved_at": utc_now().isoformat(),
            "note": _sanitize_text(approval_note, max_length=1000),
        }
    )
    approvals["approvals"] = approval_list
    request.approval_json = sanitize_report_payload(approvals)
    request.approval_count_received = len(approval_list)
    if request.approval_count_received >= request.approval_count_required:
        request.status = "approved"
        record = await db.get(CommercialModelLifecycleRecord, request.lifecycle_record_id)
        if record:
            record.previous_lifecycle_state = record.lifecycle_state
            record.lifecycle_state = request.target_state
            record.state_changed_at = utc_now()
            record.updated_at = utc_now()
            if request.target_state in ("approved", "promoted"):
                record.approval_required = False
            await db.flush()
        request.completed_at = utc_now()
    await db.flush()
    await _log_audit(
        db,
        action="promotion_request_approved",
        status="success",
        payload={"promotion_request_id": str(request.id), "approved_by": approved_by},
        result={"status": request.status, "approval_count": request.approval_count_received},
    )
    return request


async def reject_promotion_request(
    db: AsyncSession,
    promotion_request_id: UUID,
    *,
    rejected_by: str | None = None,
    reason: str | None = None,
) -> CommercialModelPromotionRequest:
    request = await db.get(CommercialModelPromotionRequest, promotion_request_id)
    if not request:
        raise ValueError("Promotion request not found")
    if request.status != "pending":
        raise ValueError(f"Cannot reject request in status: {request.status}")
    request.status = "rejected"
    request.completed_at = utc_now()
    await db.flush()
    await _log_audit(
        db,
        action="promotion_request_rejected",
        status="success",
        payload={"promotion_request_id": str(request.id), "rejected_by": rejected_by},
        result={"reason": reason},
    )
    return request


async def execute_promotion(
    db: AsyncSession,
    promotion_request_id: UUID,
    *,
    executed_by: str | None = None,
) -> dict[str, Any]:
    request = await db.get(CommercialModelPromotionRequest, promotion_request_id)
    if not request:
        raise ValueError("Promotion request not found")
    if request.status != "approved":
        raise ValueError(
            f"Promotion request must be approved before execution, current status: {request.status}"
        )
    record = await db.get(CommercialModelLifecycleRecord, request.lifecycle_record_id)
    if not record:
        raise ValueError("Lifecycle record not found")
    receipt_payload = {
        "promotion_request_id": str(request.id),
        "lifecycle_record_id": str(record.id),
        "model_name": record.model_name,
        "from_state": request.source_state,
        "to_state": request.target_state,
        "executed_by": _sanitize_text(executed_by) or "system",
        "executed_at": utc_now().isoformat(),
        "checksum_sha256": record.checksum_sha256,
        "manifest_hash": record.manifest_hash,
    }
    receipt_hash = hashlib.sha256(
        _canonical_json(sanitize_report_payload(receipt_payload)).encode("utf-8")
    ).hexdigest()
    request.immutable_receipt_hash = receipt_hash
    request.status = "executed"
    record.previous_lifecycle_state = record.lifecycle_state
    record.lifecycle_state = request.target_state
    record.state_changed_at = utc_now()
    record.updated_at = utc_now()
    await db.flush()
    await _log_audit(
        db,
        action="promotion_executed",
        status="success",
        payload={"promotion_request_id": str(request.id), "model_name": record.model_name},
        result={"to_state": request.target_state, "receipt_hash": receipt_hash},
    )
    return {"executed": True, "receipt_hash": receipt_hash, "to_state": request.target_state}


async def create_offline_promotion_bundle(
    db: AsyncSession,
    *,
    lifecycle_record_id: UUID,
    requested_by: str | None = None,
    media_ref: str | None = None,
    media_uuid: str | None = None,
    target_cluster_id: str | None = None,
    chain_of_custody_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = await db.get(CommercialModelLifecycleRecord, lifecycle_record_id)
    if not record:
        raise ValueError("Lifecycle record not found")
    if record.lifecycle_state not in ("approved", "promoted"):
        raise ValueError(
            f"Model must be approved or promoted for offline bundle, current state: {record.lifecycle_state}"
        )
    settings = get_settings()
    if record.export_restricted and not settings.commercial_sovereign_governance_enabled:
        raise ValueError("Cannot export sovereign-restricted model without sovereign governance")
    manifest = sanitize_report_payload(
        {
            "model_name": record.model_name,
            "model_alias": record.model_alias,
            "model_version": record.model_version,
            "provider": record.provider,
            "checksum_sha256": record.checksum_sha256,
            "manifest_hash": record.manifest_hash,
            "lifecycle_state": record.lifecycle_state,
            "sovereign_restricted": record.sovereign_restricted,
            "export_restricted": record.export_restricted,
            "source_cluster_id": record.cluster_id,
            "target_cluster_id": target_cluster_id,
            "media_ref": _sanitize_text(media_ref, max_length=512),
            "media_uuid": _sanitize_text(media_uuid, max_length=128),
            "created_at": utc_now().isoformat(),
        }
    )
    manifest_hash = hashlib.sha256(_canonical_json(manifest).encode("utf-8")).hexdigest()
    manifest["manifest_hash"] = manifest_hash
    signature = await sign_model_manifest(manifest)
    request = await create_promotion_request(
        db,
        lifecycle_record_id=lifecycle_record_id,
        request_type="offline_import",
        requested_by=requested_by,
        target_state="promoted",
        source_state=record.lifecycle_state,
        reason="Offline promotion bundle",
        media_ref=media_ref,
        chain_of_custody_json=chain_of_custody_json,
    )
    request.signed_manifest_hash = manifest_hash
    await db.flush()
    await _log_audit(
        db,
        action="offline_promotion_bundle_created",
        status="success",
        payload={"lifecycle_record_id": str(lifecycle_record_id), "model_name": record.model_name},
        result={"manifest_hash": manifest_hash, "promotion_request_id": str(request.id)},
    )
    return {
        "promotion_request_id": str(request.id),
        "manifest": manifest,
        "signature": signature,
        "manifest_hash": manifest_hash,
    }


async def import_offline_promotion(
    db: AsyncSession,
    *,
    manifest: dict[str, Any],
    signature: str | None = None,
    imported_by: str | None = None,
    chain_of_custody_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    model_name = manifest.get("model_name")
    manifest_hash = manifest.get("manifest_hash")
    checksum_sha256 = manifest.get("checksum_sha256")
    source_cluster_id = manifest.get("source_cluster_id")
    if not model_name or not manifest_hash:
        raise ValueError("Manifest must include model_name and manifest_hash")
    if signature and not await verify_model_signature(manifest, signature):
        raise ValueError("Invalid manifest signature")
    if await is_bundle_revoked(db, manifest_hash):
        raise ValueError("Manifest revoked by offline CRL")
    if checksum_sha256 and await is_bundle_revoked(db, checksum_sha256):
        raise ValueError("Model checksum revoked by offline CRL")
    if source_cluster_id and await is_peer_revoked(db, source_cluster_id):
        raise ValueError("Source peer revoked by offline CRL")
    sanitized_chain = (
        sanitize_report_payload(chain_of_custody_json) if chain_of_custody_json else None
    )
    if sanitized_chain:
        chain_check = await validate_chain_of_custody(sanitized_chain)
        if not chain_check["valid"]:
            raise ValueError(f"Invalid chain of custody: {chain_check['reason']}")
    provenance = await create_provenance_attestation(
        db,
        source_type="airgap",
        source_uri=manifest.get("media_ref"),
        source_cluster_id=source_cluster_id,
        imported_by=imported_by,
        import_method="airgap",
        artifact_hash=manifest_hash,
        evidence_json=sanitize_report_payload(manifest),
        chain_of_custody_json=sanitized_chain,
    )
    record = await discover_model_from_manifest(
        db,
        manifest=manifest,
        provenance_id=provenance.id,
        imported_by=imported_by,
    )
    await _log_audit(
        db,
        action="offline_promotion_imported",
        status="success",
        payload={"model_name": model_name, "manifest_hash": manifest_hash},
        result={"lifecycle_record_id": str(record.id), "provenance_id": str(provenance.id)},
    )
    return {
        "lifecycle_record_id": str(record.id),
        "provenance_id": str(provenance.id),
        "lifecycle_state": record.lifecycle_state,
    }


async def discover_model_from_manifest(
    db: AsyncSession,
    *,
    manifest: dict[str, Any],
    provenance_id: UUID | None = None,
    imported_by: str | None = None,
) -> CommercialModelLifecycleRecord:
    from app.services.models.model_lifecycle_manager import discover_model

    return await discover_model(
        db,
        model_name=manifest.get("model_name", "unknown"),
        model_alias=manifest.get("model_alias"),
        model_version=manifest.get("model_version"),
        provider=manifest.get("provider"),
        checksum_sha256=manifest.get("checksum_sha256"),
        manifest_hash=manifest.get("manifest_hash"),
        provenance_id=provenance_id,
        sovereign_restricted=manifest.get("sovereign_restricted", False),
        export_restricted=manifest.get("export_restricted", False),
        cluster_id=manifest.get("source_cluster_id"),
        metadata_json={"imported_by": imported_by, "import_method": "offline_promotion"},
    )


async def list_promotion_requests(
    db: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[CommercialModelPromotionRequest]:
    stmt = select(CommercialModelPromotionRequest).order_by(
        desc(CommercialModelPromotionRequest.created_at)
    )
    if status:
        stmt = stmt.where(CommercialModelPromotionRequest.status == status)
    stmt = stmt.limit(min(max(limit, 1), 500))
    result = await db.execute(stmt)
    return result.scalars().all()


def serialize_promotion_request(
    request: CommercialModelPromotionRequest,
    *,
    sensitive: bool = False,
) -> dict[str, Any]:
    def _short(value: str | None) -> str | None:
        if not value:
            return None
        return value if sensitive else value[:12]

    return sanitize_report_payload(
        {
            "id": str(request.id),
            "lifecycle_record_id": str(request.lifecycle_record_id),
            "request_type": request.request_type,
            "requested_by": request.requested_by,
            "target_state": request.target_state,
            "source_state": request.source_state,
            "approval_count_required": request.approval_count_required,
            "approval_count_received": request.approval_count_received,
            "status": request.status,
            "reason": request.reason,
            "bundle_id": str(request.bundle_id) if request.bundle_id else None,
            "signed_manifest_hash": _short(request.signed_manifest_hash),
            "immutable_receipt_hash": _short(request.immutable_receipt_hash),
            "media_ref": request.media_ref,
            "created_at": request.created_at.isoformat(),
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
        }
    )
