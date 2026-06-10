# Owner: commercial-ops
import uuid
from typing import Any

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.commercial.commercial_model_supply_chain import (
    CommercialModelIntegrityEvent,
    CommercialModelIntegrityScan,
    CommercialModelPromotionBundle,
    CommercialModelProvenanceAttestation,
    CommercialModelRevocationRecord,
    CommercialRuntimeModelAttestation,
    CommercialSignedModelRegistryEntry,
)
from app.models.core.model_registry import ModelRegistry
from app.services.auth import require_admin
from app.services.models.model_promotion_bundles import (
    create_model_promotion_bundle,
    list_bundles,
    promote_model_from_bundle,
    reject_model_bundle,
    verify_model_promotion_bundle,
)
from app.services.models.model_provenance import (
    create_provenance_attestation,
)
from app.services.models.runtime_attestation import serialize_runtime_attestation
from app.services.models.runtime_integrity_monitor import (
    quarantine_runtime_model,
    scan_registered_models,
    summarize_integrity_status,
)
from app.services.models.signed_model_registry import (
    approve_model,
    latest_registry_map,
    quarantine_model,
    register_model_manifest,
    revoke_model,
    verify_model_checksum,
    verify_model_signature,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    tags=["admin", "model-supply-chain"],
    dependencies=[Depends(require_admin)],
)


class RegisterModelPayload(BaseModel):
    model_name: str
    model_alias: str | None = None
    model_version: str | None = None
    provider: str | None = None
    model_file_path: str | None = None
    model_format: str = Field(pattern="^(gguf|safetensors|onnx|api|other)$")
    checksum_sha256: str | None = None
    signature: str | None = None
    provenance_id: uuid.UUID | None = None
    tenant_scope_json: dict[str, Any] | None = None
    trust_state: str | None = Field(default=None, pattern="^(trusted|pending|untrusted|quarantined|revoked)$")


class ApproveModelPayload(BaseModel):
    approved_by: str | None = None


class QuarantineModelPayload(BaseModel):
    reason: str
    revoked_by: str | None = None


class RevokeModelPayload(BaseModel):
    reason: str
    revocation_type: str = Field(pattern="^(checksum_mismatch|policy_violation|security_risk|manual|expired|crl)$")
    revoked_by: str | None = None


class ProvenancePayload(BaseModel):
    source_type: str = Field(pattern="^(local_file|huggingface|vendor|airgap|manual|api_provider)$")
    source_uri: str | None = None
    source_cluster_id: str | None = None
    imported_by: str | None = None
    import_method: str = Field(pattern="^(online|airgap|manual|api)$")
    artifact_hash: str
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    chain_of_custody_json: dict[str, Any] | None = None


class BundlePayload(BaseModel):
    bundle_name: str
    registry_entry_id: uuid.UUID
    source_cluster_id: str | None = None
    target_cluster_id: str | None = None
    include_signature: bool = True


class RejectBundlePayload(BaseModel):
    reason: str


class ManualIntegrityScanPayload(BaseModel):
    scan_type: str = Field(default="manual", pattern="^(boot|scheduled|manual|runtime_validation|federated)$")


def _serialize_registry_entry(entry: CommercialSignedModelRegistryEntry) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "model_name": entry.model_name,
        "model_alias": entry.model_alias,
        "model_version": entry.model_version,
        "provider": entry.provider,
        "model_file_path": entry.model_file_path,
        "model_format": entry.model_format,
        "checksum_sha256": entry.checksum_sha256,
        "manifest_hash": entry.manifest_hash,
        "signature": entry.signature,
        "provenance_id": str(entry.provenance_id) if entry.provenance_id else None,
        "trust_state": entry.trust_state,
        "tenant_scope_json": entry.tenant_scope_json,
        "approved_by": entry.approved_by,
        "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def _serialize_integrity_scan(item: CommercialModelIntegrityScan) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "registry_entry_id": str(item.registry_entry_id) if item.registry_entry_id else None,
            "model_name": item.model_name,
            "scan_type": item.scan_type,
            "expected_checksum": (item.expected_checksum or "")[:12] or None,
            "observed_checksum": (item.observed_checksum or "")[:12] or None,
            "integrity_status": item.integrity_status,
            "scan_duration_ms": item.scan_duration_ms,
            "node_id": item.node_id,
            "cluster_id": item.cluster_id,
            "metadata_json": item.metadata_json or {},
            "created_at": item.created_at.isoformat(),
        }
    )


def _serialize_integrity_event(item: CommercialModelIntegrityEvent) -> dict[str, Any]:
    return sanitize_report_payload(
        {
            "id": str(item.id),
            "model_name": item.model_name,
            "event_type": item.event_type,
            "severity": item.severity,
            "summary": item.summary,
            "registry_entry_id": str(item.registry_entry_id) if item.registry_entry_id else None,
            "node_id": item.node_id,
            "cluster_id": item.cluster_id,
            "immutable_hash": (item.immutable_hash or "")[:12] or None,
            "created_at": item.created_at.isoformat(),
        }
    )


def _serialize_provenance(item: CommercialModelProvenanceAttestation) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "source_type": item.source_type,
        "source_uri": item.source_uri,
        "source_cluster_id": item.source_cluster_id,
        "imported_by": item.imported_by,
        "import_method": item.import_method,
        "artifact_hash": item.artifact_hash,
        "evidence_json": item.evidence_json,
        "chain_of_custody_json": item.chain_of_custody_json,
        "created_at": item.created_at.isoformat(),
    }


def _serialize_bundle(item: CommercialModelPromotionBundle) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "bundle_name": item.bundle_name,
        "source_cluster_id": item.source_cluster_id,
        "target_cluster_id": item.target_cluster_id,
        "manifest_json": item.manifest_json,
        "manifest_hash": item.manifest_hash,
        "signature": item.signature,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
        "promoted_at": item.promoted_at.isoformat() if item.promoted_at else None,
    }


@router.get("/supply-chain/registry")
async def list_supply_chain_registry(db: AsyncSession = Depends(get_db_session)):
    rows = await db.execute(
        select(CommercialSignedModelRegistryEntry).order_by(desc(CommercialSignedModelRegistryEntry.updated_at))
    )
    return {"items": [_serialize_registry_entry(item) for item in rows.scalars().all()]}


@router.post("/supply-chain/register", status_code=201)
async def post_supply_chain_register(payload: RegisterModelPayload, db: AsyncSession = Depends(get_db_session)):
    try:
        entry = await register_model_manifest(db, **payload.model_dump())
        await db.commit()
        await db.refresh(entry)
        return _serialize_registry_entry(entry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/supply-chain/{entry_id}/verify")
async def post_supply_chain_verify(entry_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    entry = await db.get(CommercialSignedModelRegistryEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    manifest = sanitize_report_payload(
        {
            "model_name": entry.model_name,
            "model_alias": entry.model_alias,
            "model_version": entry.model_version,
            "provider": entry.provider,
            "model_file_path": entry.model_file_path,
            "model_format": entry.model_format,
            "checksum_sha256": entry.checksum_sha256,
            "provenance_id": str(entry.provenance_id) if entry.provenance_id else None,
            "tenant_scope_json": entry.tenant_scope_json,
        }
    )
    checksum = await verify_model_checksum(db, entry)
    signature_valid = await verify_model_signature(manifest, entry.signature) if entry.signature else False
    await db.commit()
    return {"checksum": checksum, "signature_valid": signature_valid}


@router.get("/integrity/scans")
async def list_integrity_scans(
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    rows = await db.execute(
        select(CommercialModelIntegrityScan)
        .order_by(desc(CommercialModelIntegrityScan.created_at))
        .limit(min(max(limit, 1), 500))
    )
    return {"items": [_serialize_integrity_scan(item) for item in rows.scalars().all()]}


@router.post("/integrity/scan")
async def post_integrity_scan(payload: ManualIntegrityScanPayload, db: AsyncSession = Depends(get_db_session)):
    result = await scan_registered_models(db, scan_type=payload.scan_type)
    await db.commit()
    return result


@router.get("/integrity/events")
async def list_integrity_events(
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    rows = await db.execute(
        select(CommercialModelIntegrityEvent)
        .order_by(desc(CommercialModelIntegrityEvent.created_at))
        .limit(min(max(limit, 1), 500))
    )
    return {"items": [_serialize_integrity_event(item) for item in rows.scalars().all()]}


@router.get("/integrity/attestations")
async def list_integrity_attestations(
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
):
    rows = await db.execute(
        select(CommercialRuntimeModelAttestation)
        .order_by(desc(CommercialRuntimeModelAttestation.attested_at))
        .limit(min(max(limit, 1), 500))
    )
    return {"items": [serialize_runtime_attestation(item) for item in rows.scalars().all()]}


@router.post("/integrity/quarantine/{entry_id}")
async def post_integrity_quarantine(entry_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    entry = await db.get(CommercialSignedModelRegistryEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    model = (
        await db.execute(
            select(ModelRegistry).where(
                (ModelRegistry.model_id == entry.model_name)
                | (ModelRegistry.model_alias == entry.model_alias)
            )
        )
    ).scalar_one_or_none()
    result = await quarantine_runtime_model(
        db,
        entry=entry,
        model=model,
        reason="manual runtime integrity quarantine",
    )
    await db.commit()
    return result


@router.post("/integrity/reverify/{entry_id}")
async def post_integrity_reverify(entry_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    entry = await db.get(CommercialSignedModelRegistryEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    model = (
        await db.execute(
            select(ModelRegistry).where(
                (ModelRegistry.model_id == entry.model_name)
                | (ModelRegistry.model_alias == entry.model_alias)
            )
        )
    ).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Runtime model not found")
    result = await scan_registered_models(db, scan_type="runtime_validation")
    if entry.trust_state == "quarantined":
        latest_scan = (
            await db.execute(
                select(CommercialModelIntegrityScan)
                .where(CommercialModelIntegrityScan.registry_entry_id == entry.id)
                .order_by(desc(CommercialModelIntegrityScan.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest_scan and latest_scan.integrity_status == "verified":
            entry.trust_state = "trusted"
            model.status = "configured"
    await db.commit()
    return {"reverified": True, "result": result, "trust_state": entry.trust_state}


@router.get("/integrity/status")
async def get_integrity_status(db: AsyncSession = Depends(get_db_session)):
    return await summarize_integrity_status(db)


@router.post("/supply-chain/{entry_id}/approve")
async def post_supply_chain_approve(
    entry_id: uuid.UUID,
    payload: ApproveModelPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        entry = await approve_model(db, entry_id, approved_by=payload.approved_by)
        await db.commit()
        await db.refresh(entry)
        return _serialize_registry_entry(entry)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/supply-chain/{entry_id}/quarantine")
async def post_supply_chain_quarantine(
    entry_id: uuid.UUID,
    payload: QuarantineModelPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        entry = await quarantine_model(db, entry_id, reason=payload.reason, revoked_by=payload.revoked_by)
        await db.commit()
        await db.refresh(entry)
        return _serialize_registry_entry(entry)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/supply-chain/{entry_id}/revoke")
async def post_supply_chain_revoke(
    entry_id: uuid.UUID,
    payload: RevokeModelPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        record = await revoke_model(
            db,
            entry_id=entry_id,
            reason=payload.reason,
            revocation_type=payload.revocation_type,
            revoked_by=payload.revoked_by,
        )
        await db.commit()
        return {
            "id": str(record.id),
            "registry_entry_id": str(record.registry_entry_id) if record.registry_entry_id else None,
            "model_name": record.model_name,
            "reason": record.reason,
            "revocation_type": record.revocation_type,
            "revoked_by": record.revoked_by,
            "created_at": record.created_at.isoformat(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/supply-chain/provenance")
async def list_supply_chain_provenance(db: AsyncSession = Depends(get_db_session)):
    rows = await db.execute(
        select(CommercialModelProvenanceAttestation).order_by(desc(CommercialModelProvenanceAttestation.created_at))
    )
    return {"items": [_serialize_provenance(item) for item in rows.scalars().all()]}


@router.post("/supply-chain/provenance", status_code=201)
async def post_supply_chain_provenance(payload: ProvenancePayload, db: AsyncSession = Depends(get_db_session)):
    try:
        item = await create_provenance_attestation(db, **payload.model_dump())
        await db.commit()
        await db.refresh(item)
        return _serialize_provenance(item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/supply-chain/bundles")
async def get_supply_chain_bundles(db: AsyncSession = Depends(get_db_session)):
    return {"items": [_serialize_bundle(item) for item in await list_bundles(db)]}


@router.post("/supply-chain/bundles", status_code=201)
async def post_supply_chain_bundle(payload: BundlePayload, db: AsyncSession = Depends(get_db_session)):
    try:
        item = await create_model_promotion_bundle(db, **payload.model_dump())
        await db.commit()
        await db.refresh(item)
        return _serialize_bundle(item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/supply-chain/bundles/{bundle_id}/verify")
async def post_supply_chain_bundle_verify(bundle_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    bundle = await db.get(CommercialModelPromotionBundle, bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    result = await verify_model_promotion_bundle(db, bundle)
    await db.commit()
    return result


@router.post("/supply-chain/bundles/{bundle_id}/promote")
async def post_supply_chain_bundle_promote(bundle_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    try:
        entry = await promote_model_from_bundle(db, bundle_id, imported_by="admin")
        await db.commit()
        await db.refresh(entry)
        return _serialize_registry_entry(entry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/supply-chain/bundles/{bundle_id}/reject")
async def post_supply_chain_bundle_reject(
    bundle_id: uuid.UUID,
    payload: RejectBundlePayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        bundle = await reject_model_bundle(db, bundle_id, reason=payload.reason)
        await db.commit()
        await db.refresh(bundle)
        return _serialize_bundle(bundle)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/supply-chain/status")
async def get_supply_chain_status(db: AsyncSession = Depends(get_db_session)):
    registry_rows = await db.execute(select(CommercialSignedModelRegistryEntry))
    entries = registry_rows.scalars().all()
    revocations = await db.execute(select(func.count(CommercialModelRevocationRecord.id)))
    bundles = await db.execute(select(func.count(CommercialModelPromotionBundle.id)))
    state_counts: dict[str, int] = {}
    for entry in entries:
        state_counts[entry.trust_state] = state_counts.get(entry.trust_state, 0) + 1
    latest = await latest_registry_map(db)
    return {
        "registry_total": len(entries),
        "trust_state_counts": state_counts,
        "revocation_total": int(revocations.scalar() or 0),
        "bundle_total": int(bundles.scalar() or 0),
        "enforcement_mode": get_settings().commercial_model_trust_enforcement_mode,
        "require_trusted_for_routing": get_settings().commercial_model_require_trusted_for_routing,
        "model_risk_summary": {
            "trusted": state_counts.get("trusted", 0),
            "pending_review": state_counts.get("pending", 0),
            "blocked": sum(state_counts.get(item, 0) for item in ("untrusted", "quarantined", "revoked")),
        },
        "tracked_models": sorted(latest.keys()),
    }
