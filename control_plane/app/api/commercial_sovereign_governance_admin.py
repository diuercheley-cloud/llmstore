# Owner: commercial-ops
import uuid
from datetime import datetime
from typing import Any

from app.models.commercial.commercial_sovereign_governance import (
    CommercialAirgapSyncPackage,
    CommercialOfflineRevocationList,
)
from app.services.auth import require_admin
from app.services.governance.airgap_sync import (
    create_airgap_package,
    export_airgap_package,
    import_airgap_package,
    reject_package,
    validate_chain_of_custody,
)
from app.services.runtime_dependencies import get_db_session
from app.services.security.hardware_attestation import (
    collect_attestation_evidence,
    summarize_attestation_status,
    verify_attestation_record,
)
from app.services.security.offline_crl import apply_offline_crl, create_offline_crl
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    tags=["admin", "sovereign", "airgap"],
    dependencies=[Depends(require_admin)],
)


class AirgapPackageCreatePayload(BaseModel):
    package_type: str = Field(
        pattern="^(policy_bundle|audit_trail|evidence|crl|full_governance_snapshot)$"
    )
    source_cluster_id: str
    target_cluster_id: str | None = None
    package_version: str = "1.0"
    classification: str | None = None
    payload: dict[str, Any]
    chain_of_custody_json: dict[str, Any]
    expires_at: datetime | None = None


class AirgapPackageExportPayload(BaseModel):
    payload: dict[str, Any]
    classification: str | None = None
    key_fingerprint: str | None = None


class AirgapImportPayload(BaseModel):
    package_bundle: dict[str, Any]


class PackageRejectPayload(BaseModel):
    reason: str


class OfflineCRLPayload(BaseModel):
    crl_version: str
    revoked_key_fingerprints_json: list[str] = Field(default_factory=list)
    revoked_bundle_hashes_json: list[str] = Field(default_factory=list)
    revoked_peer_ids_json: list[str] = Field(default_factory=list)
    reason: str | None = None
    expires_at: datetime | None = None


class AttestationCollectPayload(BaseModel):
    cluster_id: str
    node_id: str | None = None
    attestation_type: str = Field(
        default="placeholder", pattern="^(tpm|secure_boot|sgx|sev|placeholder)$"
    )
    status: str = Field(default="unknown", pattern="^(trusted|untrusted|unknown|expired)$")
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None


class AttestationVerifyPayload(BaseModel):
    record_id: uuid.UUID


@router.get("/admin/governance/airgap/packages")
async def list_airgap_packages(db: AsyncSession = Depends(get_db_session)):
    rows = await db.execute(
        select(CommercialAirgapSyncPackage).order_by(desc(CommercialAirgapSyncPackage.created_at))
    )
    return rows.scalars().all()


@router.post("/admin/governance/airgap/packages", status_code=201)
async def post_airgap_package(
    payload: AirgapPackageCreatePayload, db: AsyncSession = Depends(get_db_session)
):
    try:
        item = await create_airgap_package(
            db,
            package_type=payload.package_type,
            payload=payload.payload,
            source_cluster_id=payload.source_cluster_id,
            target_cluster_id=payload.target_cluster_id,
            package_version=payload.package_version,
            classification=payload.classification,
            chain_of_custody_json=payload.chain_of_custody_json,
            expires_at=payload.expires_at,
        )
        await db.commit()
        await db.refresh(item)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/admin/governance/airgap/packages/{package_id}/export")
async def post_airgap_export(
    package_id: uuid.UUID,
    payload: AirgapPackageExportPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        item = await export_airgap_package(
            db,
            package_id,
            payload=payload.payload,
            classification=payload.classification,
            key_fingerprint=payload.key_fingerprint,
        )
        await db.commit()
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/admin/governance/airgap/packages/import", status_code=201)
async def post_airgap_import(
    payload: AirgapImportPayload, db: AsyncSession = Depends(get_db_session)
):
    try:
        item = await import_airgap_package(db, payload.package_bundle)
        await db.commit()
        await db.refresh(item)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/admin/governance/airgap/packages/{package_id}/verify")
async def post_airgap_verify(package_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    package = await db.get(CommercialAirgapSyncPackage, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    chain = await validate_chain_of_custody(package.chain_of_custody_json)
    if not package.signature:
        raise HTTPException(status_code=400, detail="Missing package signature")
    if not chain["valid"]:
        raise HTTPException(status_code=400, detail=chain["reason"])
    package.status = "verified"
    await db.commit()
    return {"status": "verified", "manifest_hash": package.manifest_hash}


@router.post("/admin/governance/airgap/packages/{package_id}/reject")
async def post_airgap_reject(
    package_id: uuid.UUID,
    payload: PackageRejectPayload,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        item = await reject_package(db, package_id, reason=payload.reason)
        await db.commit()
        await db.refresh(item)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/admin/security/offline-crl")
async def list_offline_crl(db: AsyncSession = Depends(get_db_session)):
    rows = await db.execute(
        select(CommercialOfflineRevocationList).order_by(
            desc(CommercialOfflineRevocationList.created_at)
        )
    )
    return rows.scalars().all()


@router.post("/admin/security/offline-crl", status_code=201)
async def post_offline_crl(payload: OfflineCRLPayload, db: AsyncSession = Depends(get_db_session)):
    item = await create_offline_crl(db, **payload.model_dump())
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/admin/security/offline-crl/{crl_id}/apply")
async def post_apply_offline_crl(crl_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    try:
        result = await apply_offline_crl(db, crl_id)
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/admin/security/hardware-attestation")
async def list_hardware_attestations(db: AsyncSession = Depends(get_db_session)):
    return await summarize_attestation_status(db)


@router.post("/admin/security/hardware-attestation/collect", status_code=201)
async def post_collect_attestation(
    payload: AttestationCollectPayload, db: AsyncSession = Depends(get_db_session)
):
    item = await collect_attestation_evidence(db, **payload.model_dump())
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/admin/security/hardware-attestation/verify")
async def post_verify_attestation(
    payload: AttestationVerifyPayload, db: AsyncSession = Depends(get_db_session)
):
    try:
        item = await verify_attestation_record(db, payload.record_id)
        await db.commit()
        await db.refresh(item)
        return item
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
