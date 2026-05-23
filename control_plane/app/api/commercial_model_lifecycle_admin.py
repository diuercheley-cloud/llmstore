# Owner: commercial-ops
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.commercial_model_lifecycle import (
    CommercialModelLifecycleRecord,
    CommercialModelLineage,
    CommercialModelPromotionRequest,
    CommercialModelRollbackRecord,
    CommercialOfflineModelVerification,
    VALID_LIFECYCLE_STATES,
)
from app.services.auth import require_admin
from app.services.models.model_lifecycle_manager import (
    discover_model,
    enforce_lifecycle_gates,
    get_lifecycle_by_model,
    get_lifecycle_record,
    list_lifecycle_records,
    serialize_lifecycle_record,
    serialize_offline_verification,
    stage_model,
    summarize_lifecycle_status,
    transition_lifecycle_state,
    verify_offline_model,
)
from app.services.models.model_lineage import (
    create_lineage_entry,
    get_lineage_dag,
    list_lineage_entries,
    serialize_lineage_entry,
    validate_lineage,
    verify_provenance_chain,
)
from app.services.models.model_promotion import (
    approve_promotion_request,
    create_offline_promotion_bundle,
    create_promotion_request,
    execute_promotion,
    import_offline_promotion,
    list_promotion_requests,
    reject_promotion_request,
    serialize_promotion_request,
)
from app.services.models.model_quarantine import (
    list_quarantined_models,
    list_rollback_records,
    quarantine_lifecycle_model,
    release_from_quarantine,
    rollback_model,
    serialize_rollback_record,
)
from app.services.routing.commercial_report_export import sanitize_report_payload

router = APIRouter(
    prefix="/admin/models/lifecycle",
    tags=["admin", "model-lifecycle"],
    dependencies=[Depends(require_admin)],
)

portal_router = APIRouter(
    prefix="/portal/models",
    tags=["portal", "model-lifecycle"],
    dependencies=[Depends(require_admin)],
)


class DiscoverModelPayload(BaseModel):
    model_name: str
    model_alias: str | None = None
    model_version: str | None = None
    provider: str | None = None
    checksum_sha256: str | None = None
    manifest_hash: str | None = None
    registry_entry_id: uuid.UUID | None = None
    tenant_scope_json: dict[str, Any] | None = None
    provenance_id: uuid.UUID | None = None
    sovereign_restricted: bool = False
    export_restricted: bool = False
    cluster_id: str | None = None
    node_id: str | None = None


class TransitionPayload(BaseModel):
    target_state: str = Field(pattern=r"^(discovered|staged|pending_approval|approved|promoted|quarantined|revoked|rolled_back|archived)$")
    changed_by: str | None = None
    reason: str | None = None


class StageModelPayload(BaseModel):
    staged_by: str | None = None


class PromotionRequestPayload(BaseModel):
    lifecycle_record_id: uuid.UUID
    request_type: str = Field(pattern=r"^(staged_to_pending|pending_to_approved|approved_to_promoted|offline_import|rollback_promotion)$")
    requested_by: str | None = None
    target_state: str = Field(pattern=r"^(pending_approval|approved|promoted)$")
    source_state: str | None = None
    approval_count_required: int = Field(default=1, ge=1)
    reason: str | None = None
    bundle_id: uuid.UUID | None = None
    media_ref: str | None = None
    chain_of_custody_json: dict[str, Any] | None = None


class ApprovePromotionPayload(BaseModel):
    approved_by: str | None = None
    approval_note: str | None = None


class RejectPromotionPayload(BaseModel):
    rejected_by: str | None = None
    reason: str | None = None


class ExecutePromotionPayload(BaseModel):
    executed_by: str | None = None


class QuarantinePayload(BaseModel):
    reason: str = Field(pattern=r"^(checksum_mismatch|signature_invalid|provenance_invalid|crl_revoked|policy_violation|manual_quarantine|attestation_failure|lineage_broken|sovereign_violation|runtime_drift)$")
    quarantined_by: str | None = None


class ReleaseQuarantinePayload(BaseModel):
    released_by: str | None = None
    target_state: str = Field(default="staged", pattern=r"^(staged|pending_approval)$")
    reason: str | None = None


class RollbackPayload(BaseModel):
    rollback_to_state: str = Field(default="staged", pattern=r"^(staged|pending_approval)$")
    rollback_reason: str
    rolled_back_by: str | None = None
    promotion_request_id: uuid.UUID | None = None
    predecessor_checksum: str | None = None
    chain_of_custody_json: dict[str, Any] | None = None


class LineageEntryPayload(BaseModel):
    lifecycle_record_id: uuid.UUID
    parent_lineage_id: uuid.UUID | None = None
    source_type: str
    source_ref: str | None = None
    source_cluster_id: str | None = None
    derivation_method: str = Field(pattern=r"^(original_import|offline_promotion|version_upgrade|finetune_derivative|quantization_derivative|merge_derivative|conversion_derivative|rollback_restoration)$")
    artifact_hash: str
    predecessor_hash: str | None = None
    provenance_id: uuid.UUID | None = None
    evidence_json: dict[str, Any] | None = None


class OfflineVerificationPayload(BaseModel):
    model_name: str
    checksum_sha256: str | None = None
    manifest_hash: str | None = None
    lifecycle_record_id: uuid.UUID | None = None
    verification_type: str = Field(default="offline_import", pattern=r"^(offline_import|usb_media|airgap_transfer|crl_check)$")
    media_ref: str | None = None
    media_uuid: str | None = None
    source_cluster_id: str | None = None
    signed_manifest: dict[str, Any] | None = None
    verified_by: str | None = None


class OfflineBundlePayload(BaseModel):
    lifecycle_record_id: uuid.UUID
    requested_by: str | None = None
    media_ref: str | None = None
    media_uuid: str | None = None
    target_cluster_id: str | None = None
    chain_of_custody_json: dict[str, Any] | None = None


class OfflineImportPayload(BaseModel):
    manifest: dict[str, Any]
    signature: str | None = None
    imported_by: str | None = None
    chain_of_custody_json: dict[str, Any] | None = None


@router.get("")
async def list_lifecycle(
    lifecycle_state: str | None = None,
    cluster_id: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    records = await list_lifecycle_records(db, lifecycle_state=lifecycle_state, cluster_id=cluster_id, limit=limit)
    return {"items": [serialize_lifecycle_record(r) for r in records]}


@router.post("", status_code=201)
async def post_discover(payload: DiscoverModelPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        record = await discover_model(db, **payload.model_dump())
        await db.commit()
        await db.refresh(record)
        return serialize_lifecycle_record(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/status")
async def get_lifecycle_status(db: AsyncSession = Depends(get_db_session)):
    return await summarize_lifecycle_status(db)


@router.get("/dashboard")
async def get_lifecycle_dashboard(db: AsyncSession = Depends(get_db_session)):
    status = await summarize_lifecycle_status(db)
    quarantined = await list_quarantined_models(db, limit=20)
    recent_rollbacks = await list_rollback_records(db, limit=20)
    recent_promotions = await list_promotion_requests(db, status="executed", limit=20)
    pending_approvals = await list_promotion_requests(db, status="pending", limit=20)
    verification_rows = await db.execute(
        select(CommercialOfflineModelVerification)
        .order_by(desc(CommercialOfflineModelVerification.created_at))
        .limit(20)
    )
    recent_verifications = verification_rows.scalars().all()
    return sanitize_report_payload({
        "status_summary": status,
        "quarantine_events": [serialize_lifecycle_record(r) for r in quarantined],
        "rollback_history": [serialize_rollback_record(r) for r in recent_rollbacks],
        "recent_promotions": [serialize_promotion_request(r) for r in recent_promotions],
        "pending_approvals": [serialize_promotion_request(r) for r in pending_approvals],
        "recent_verifications": [serialize_offline_verification(v) for v in recent_verifications],
        "attestation_status": {
            "attestation_bound_count": status.get("fully_verified", 0),
            "pending_count": status.get("pending_approval", 0),
        },
    })


@router.get("/{lifecycle_id}")
async def get_lifecycle_detail(lifecycle_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    record = await get_lifecycle_record(db, lifecycle_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lifecycle record not found")
    return serialize_lifecycle_record(record)


@router.post("/{lifecycle_id}/stage")
async def post_stage(lifecycle_id: uuid.UUID, payload: StageModelPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        record = await stage_model(db, lifecycle_id, staged_by=payload.staged_by)
        await db.commit()
        await db.refresh(record)
        return serialize_lifecycle_record(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{lifecycle_id}/transition")
async def post_transition(lifecycle_id: uuid.UUID, payload: TransitionPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        record = await transition_lifecycle_state(db, lifecycle_id, target_state=payload.target_state, changed_by=payload.changed_by, reason=payload.reason)
        await db.commit()
        await db.refresh(record)
        return serialize_lifecycle_record(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{lifecycle_id}/enforce-gates")
async def post_enforce_gates(lifecycle_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    record = await get_lifecycle_record(db, lifecycle_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lifecycle record not found")
    return await enforce_lifecycle_gates(db, record)


@router.post("/{lifecycle_id}/quarantine")
async def post_quarantine(lifecycle_id: uuid.UUID, payload: QuarantinePayload, db: AsyncSession = Depends(get_db_session)):
    try:
        record = await quarantine_lifecycle_model(db, lifecycle_id, reason=payload.reason, quarantined_by=payload.quarantined_by)
        await db.commit()
        await db.refresh(record)
        return serialize_lifecycle_record(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{lifecycle_id}/release-quarantine")
async def post_release_quarantine(lifecycle_id: uuid.UUID, payload: ReleaseQuarantinePayload, db: AsyncSession = Depends(get_db_session)):
    try:
        record = await release_from_quarantine(db, lifecycle_id, released_by=payload.released_by, target_state=payload.target_state, reason=payload.reason)
        await db.commit()
        await db.refresh(record)
        return serialize_lifecycle_record(record)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{lifecycle_id}/rollback")
async def post_rollback(lifecycle_id: uuid.UUID, payload: RollbackPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        rollback = await rollback_model(
            db,
            lifecycle_id,
            rollback_to_state=payload.rollback_to_state,
            rollback_reason=payload.rollback_reason,
            rolled_back_by=payload.rolled_back_by,
            promotion_request_id=payload.promotion_request_id,
            predecessor_checksum=payload.predecessor_checksum,
            chain_of_custody_json=payload.chain_of_custody_json,
        )
        await db.commit()
        await db.refresh(rollback)
        return serialize_rollback_record(rollback)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{lifecycle_id}/lineage")
async def post_lineage_entry(lifecycle_id: uuid.UUID, payload: LineageEntryPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        entry = await create_lineage_entry(
            db,
            lifecycle_record_id=payload.lifecycle_record_id,
            parent_lineage_id=payload.parent_lineage_id,
            source_type=payload.source_type,
            source_ref=payload.source_ref,
            source_cluster_id=payload.source_cluster_id,
            derivation_method=payload.derivation_method,
            artifact_hash=payload.artifact_hash,
            predecessor_hash=payload.predecessor_hash,
            provenance_id=payload.provenance_id,
            evidence_json=payload.evidence_json,
        )
        await db.commit()
        await db.refresh(entry)
        return serialize_lineage_entry(entry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{lifecycle_id}/lineage")
async def get_lineage(lifecycle_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    return await get_lineage_dag(db, lifecycle_id)


@router.get("/{lifecycle_id}/lineage/validate")
async def get_lineage_validation(lifecycle_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    return await validate_lineage(db, lifecycle_id)


@router.get("/{lifecycle_id}/lineage/provenance")
async def get_lineage_provenance(lifecycle_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    return await verify_provenance_chain(db, lifecycle_id)


@router.get("/promotions")
async def list_promotions(
    status: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    requests = await list_promotion_requests(db, status=status, limit=limit)
    return {"items": [serialize_promotion_request(r) for r in requests]}


@router.post("/promotions")
async def post_promotion_request(payload: PromotionRequestPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        request = await create_promotion_request(db, **payload.model_dump())
        await db.commit()
        await db.refresh(request)
        return serialize_promotion_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/promotions/{request_id}/approve")
async def post_promotion_approve(request_id: uuid.UUID, payload: ApprovePromotionPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        request = await approve_promotion_request(db, request_id, approved_by=payload.approved_by, approval_note=payload.approval_note)
        await db.commit()
        await db.refresh(request)
        return serialize_promotion_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/promotions/{request_id}/reject")
async def post_promotion_reject(request_id: uuid.UUID, payload: RejectPromotionPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        request = await reject_promotion_request(db, request_id, rejected_by=payload.rejected_by, reason=payload.reason)
        await db.commit()
        await db.refresh(request)
        return serialize_promotion_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/promotions/{request_id}/execute")
async def post_promotion_execute(request_id: uuid.UUID, payload: ExecutePromotionPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        result = await execute_promotion(db, request_id, executed_by=payload.executed_by)
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/offline/bundle")
async def post_offline_bundle(payload: OfflineBundlePayload, db: AsyncSession = Depends(get_db_session)):
    try:
        result = await create_offline_promotion_bundle(
            db,
            lifecycle_record_id=payload.lifecycle_record_id,
            requested_by=payload.requested_by,
            media_ref=payload.media_ref,
            media_uuid=payload.media_uuid,
            target_cluster_id=payload.target_cluster_id,
            chain_of_custody_json=payload.chain_of_custody_json,
        )
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/offline/import")
async def post_offline_import(payload: OfflineImportPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        result = await import_offline_promotion(
            db,
            manifest=payload.manifest,
            signature=payload.signature,
            imported_by=payload.imported_by,
            chain_of_custody_json=payload.chain_of_custody_json,
        )
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/offline/verify")
async def post_offline_verify(payload: OfflineVerificationPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        verification = await verify_offline_model(
            db,
            model_name=payload.model_name,
            checksum_sha256=payload.checksum_sha256,
            manifest_hash=payload.manifest_hash,
            lifecycle_record_id=payload.lifecycle_record_id,
            verification_type=payload.verification_type,
            media_ref=payload.media_ref,
            media_uuid=payload.media_uuid,
            source_cluster_id=payload.source_cluster_id,
            signed_manifest=payload.signed_manifest,
            verified_by=payload.verified_by,
        )
        await db.commit()
        await db.refresh(verification)
        return serialize_offline_verification(verification)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/quarantine/events")
async def list_quarantine_events(
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    records = await list_quarantined_models(db, limit=limit)
    return {"items": [serialize_lifecycle_record(r) for r in records]}


@router.get("/rollback/history")
async def list_rollback_history(
    lifecycle_record_id: uuid.UUID | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    records = await list_rollback_records(db, lifecycle_record_id=lifecycle_record_id, limit=limit)
    return {"items": [serialize_rollback_record(r) for r in records]}


@router.get("/lineage/entries")
async def list_all_lineage(
    lifecycle_record_id: uuid.UUID | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    entries = await list_lineage_entries(db, lifecycle_record_id=lifecycle_record_id, limit=limit)
    return {"items": [serialize_lineage_entry(e) for e in entries]}


@portal_router.get("/trust-status")
async def get_trust_status(
    model_name: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    if not model_name:
        return await summarize_lifecycle_status(db)
    record = await get_lifecycle_by_model(db, model_name)
    if not record:
        return {"model_name": model_name, "lifecycle_state": None, "trust_status": "not_found"}
    gates = await enforce_lifecycle_gates(db, record)
    return serialize_lifecycle_record(record) | {"gates": gates}
