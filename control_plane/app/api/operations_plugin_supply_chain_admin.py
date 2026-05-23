# Owner: platform-ops
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.plugin_runtime import PluginABIContract
from app.models.operations.plugin_supply_chain import (
    DependencyGovernancePolicy,
    PluginArtifactLineage,
    PluginDependencyVerification,
    PluginProvenanceRecord,
    PluginSBOMPlaceholder,
    PluginSignedArtifactPlaceholder,
    PluginSupplyChainReceipt,
    PLUGIN_PROVENANCE_SCOPES,
    PLUGIN_PROVENANCE_STATUSES,
    PLUGIN_SIGNATURE_STATUSES,
)
from app.services.operations.plugin_supply_chain.audit_events import build_plugin_supply_chain_audit_event
from app.services.operations.plugin_supply_chain.dependency_governance import DependencyGovernanceService
from app.services.operations.plugin_supply_chain.lineage_service import PluginArtifactLineageService
from app.services.operations.plugin_supply_chain.provenance_service import PluginProvenanceService
from app.services.operations.plugin_supply_chain.receipts import build_supply_chain_receipt
from app.services.operations.plugin_supply_chain.replay_verifier import PluginSupplyChainReplayVerifier
from app.services.operations.plugin_supply_chain.sbom_placeholder import PluginSBOMPlaceholderService
from app.services.operations.plugin_supply_chain.hash_utils import sha256_hex

router = APIRouter()

PROVENANCE_SERVICE = PluginProvenanceService()
SBOM_SERVICE = PluginSBOMPlaceholderService()
DEPENDENCY_SERVICE = DependencyGovernanceService()
LINEAGE_SERVICE = PluginArtifactLineageService()
REPLAY_VERIFIER = PluginSupplyChainReplayVerifier()


class ProvenanceCreateRequest(BaseModel):
    client_id: UUID
    plugin_contract_id: str
    artifact_name: str
    artifact_version: str
    provenance_scope: str
    provenance_status: str = "proposed"
    replay_safe: bool = True


class SBOMRequest(BaseModel):
    client_id: UUID
    sbom_format: str = "placeholder_v1"
    dependency_summary_json: dict[str, Any] = Field(default_factory=dict)
    denied_dependencies_json: list[str] = Field(default_factory=list)
    reproducible_build: bool = True
    offline_verifiable: bool = True


class DependencyVerificationRequest(BaseModel):
    client_id: UUID
    dependency_summary_json: dict[str, Any] = Field(default_factory=dict)
    policy_name: str = "default-plugin-supply-chain"
    denied_dependency_classes_json: list[str] = Field(default_factory=list)
    allowed_dependency_classes_json: list[str] = Field(default_factory=list)
    reproducible_build: bool = True
    offline_verifiable: bool = True
    signature_placeholder: str | None = None


class LineageRequest(BaseModel):
    client_id: UUID
    parent_artifact_hash: str | None = None


class ReplayRequest(BaseModel):
    client_id: UUID


class SignatureRequest(BaseModel):
    client_id: UUID
    signature_scope: str = "provenance_record"
    signature_status: str = "placeholder_only"


class ReceiptRequest(BaseModel):
    client_id: UUID
    receipt_type: str = "provenance_receipt"


def _serialize_provenance(item: PluginProvenanceRecord) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "plugin_contract_id": item.plugin_contract_id,
        "artifact_name": item.artifact_name,
        "artifact_version": item.artifact_version,
        "provenance_scope": item.provenance_scope,
        "provenance_status": item.provenance_status,
        "provenance_hash": item.provenance_hash,
        "replay_safe": item.replay_safe,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_sbom(item: PluginSBOMPlaceholder) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "provenance_record_id": item.provenance_record_id,
        "sbom_format": item.sbom_format,
        "dependency_summary_json": item.dependency_summary_json,
        "denied_dependencies_json": item.denied_dependencies_json,
        "reproducible_build": item.reproducible_build,
        "offline_verifiable": item.offline_verifiable,
        "sbom_hash": item.sbom_hash,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_verification(item: PluginDependencyVerification) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "provenance_record_id": item.provenance_record_id,
        "verification_status": item.verification_status,
        "replay_safe": item.replay_safe,
        "dependency_summary": json.loads(item.dependency_summary),
        "immutable_hash": item.immutable_hash,
    }


def _serialize_lineage(item: PluginArtifactLineage) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "provenance_record_id": item.provenance_record_id,
        "parent_artifact_hash": item.parent_artifact_hash,
        "lineage_hash": item.lineage_hash,
        "replay_verifiable": item.replay_verifiable,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_signature(item: PluginSignedArtifactPlaceholder) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "provenance_record_id": item.provenance_record_id,
        "signature_placeholder": item.signature_placeholder,
        "signature_scope": item.signature_scope,
        "signature_status": item.signature_status,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_receipt(item: PluginSupplyChainReceipt) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "provenance_record_id": item.provenance_record_id,
        "receipt_type": item.receipt_type,
        "payload_hash": item.payload_hash,
        "immutable_hash": item.immutable_hash,
        "signature_placeholder": item.signature_placeholder,
    }


async def _get_contract(db: AsyncSession, contract_id: str, client_id: UUID) -> PluginABIContract:
    contract = (
        await db.execute(
            select(PluginABIContract).where(
                PluginABIContract.id == contract_id,
                PluginABIContract.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Plugin contract not found")
    return contract


async def _get_provenance(db: AsyncSession, provenance_id: str, client_id: UUID) -> PluginProvenanceRecord:
    item = (
        await db.execute(
            select(PluginProvenanceRecord).where(
                PluginProvenanceRecord.id == provenance_id,
                PluginProvenanceRecord.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Provenance record not found")
    return item


@router.post("/admin/operations/plugin-supply-chain/provenance")
async def create_provenance(
    request: ProvenanceCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if request.provenance_scope not in PLUGIN_PROVENANCE_SCOPES:
        raise HTTPException(status_code=400, detail="Unsupported provenance scope")
    if request.provenance_status not in PLUGIN_PROVENANCE_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported provenance status")
    await _get_contract(db, request.plugin_contract_id, request.client_id)
    record = PROVENANCE_SERVICE.create_provenance_record(request.model_dump())
    db.add(record)
    event = build_plugin_supply_chain_audit_event(
        "provenance_created",
        str(request.client_id),
        {"provenance_id": record.id, "artifact_name": record.artifact_name},
    )
    await db.commit()
    return {"provenance": _serialize_provenance(record), "audit_event": event}


@router.get("/admin/operations/plugin-supply-chain/provenance")
async def list_provenance(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(PluginProvenanceRecord)
            .where(PluginProvenanceRecord.client_id == client_id)
            .order_by(PluginProvenanceRecord.created_at.desc())
        )
    ).scalars().all()
    return [_serialize_provenance(item) for item in rows]


@router.get("/admin/operations/plugin-supply-chain/provenance/{provenance_id}")
async def get_provenance(
    provenance_id: str,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    item = await _get_provenance(db, provenance_id, client_id)
    return {"provenance": _serialize_provenance(item), "explanation": PROVENANCE_SERVICE.explain_provenance(item)}


@router.post("/admin/operations/plugin-supply-chain/provenance/{provenance_id}/verify")
async def verify_provenance(
    provenance_id: str,
    request: ReplayRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    item = await _get_provenance(db, provenance_id, request.client_id)
    verification = PROVENANCE_SERVICE.verify_provenance(item)
    item.replay_safe = verification["replay_safe"]
    event = build_plugin_supply_chain_audit_event("provenance_verified", str(request.client_id), {"provenance_id": item.id, "status": item.provenance_status})
    await db.commit()
    return {"provenance": _serialize_provenance(item), "verification": verification, "audit_event": event}


@router.post("/admin/operations/plugin-supply-chain/provenance/{provenance_id}/revoke")
async def revoke_provenance(
    provenance_id: str,
    request: ReplayRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    item = await _get_provenance(db, provenance_id, request.client_id)
    revocation = PROVENANCE_SERVICE.revoke_provenance(item)
    item.replay_safe = False
    await db.commit()
    return {"provenance": _serialize_provenance(item), "revocation": revocation}


@router.post("/admin/operations/plugin-supply-chain/provenance/{provenance_id}/sbom")
async def generate_sbom_placeholder(
    provenance_id: str,
    request: SBOMRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    provenance = await _get_provenance(db, provenance_id, request.client_id)
    placeholder = SBOM_SERVICE.generate_sbom_placeholder(provenance, **request.model_dump(exclude={"client_id"}))
    db.add(placeholder)
    event = build_plugin_supply_chain_audit_event("sbom_generated", str(request.client_id), {"provenance_id": provenance.id, "sbom_id": placeholder.id})
    await db.commit()
    return {"sbom": _serialize_sbom(placeholder), "validation": SBOM_SERVICE.validate_sbom_placeholder(placeholder), "audit_event": event}


@router.get("/admin/operations/plugin-supply-chain/sbom")
async def list_sbom_placeholders(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(PluginSBOMPlaceholder)
            .where(PluginSBOMPlaceholder.client_id == client_id)
            .order_by(PluginSBOMPlaceholder.created_at.desc())
        )
    ).scalars().all()
    return [_serialize_sbom(item) for item in rows]


@router.post("/admin/operations/plugin-supply-chain/provenance/{provenance_id}/dependency-verify")
async def verify_dependencies(
    provenance_id: str,
    request: DependencyVerificationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    provenance = await _get_provenance(db, provenance_id, request.client_id)
    policy = DEPENDENCY_SERVICE.create_policy(
        client_id=request.client_id,
        policy_name=request.policy_name,
        denied_dependency_classes_json=request.denied_dependency_classes_json or None,
        allowed_dependency_classes_json=request.allowed_dependency_classes_json or None,
    )
    verification = DEPENDENCY_SERVICE.verify_dependencies(
        provenance,
        dependency_summary_json=request.dependency_summary_json,
        policy=policy,
        signature_placeholder=request.signature_placeholder,
        reproducible_build=request.reproducible_build,
        offline_verifiable=request.offline_verifiable,
    )
    db.add(policy)
    db.add(verification)
    event = build_plugin_supply_chain_audit_event(
        "dependency_verification_completed",
        str(request.client_id),
        {"provenance_id": provenance.id, "verification_status": verification.verification_status},
    )
    await db.commit()
    return {
        "policy": {
            "id": policy.id,
            "policy_name": policy.policy_name,
            "denied_dependency_classes_json": policy.denied_dependency_classes_json,
            "allowed_dependency_classes_json": policy.allowed_dependency_classes_json,
            "require_reproducible_builds": policy.require_reproducible_builds,
            "require_offline_verification": policy.require_offline_verification,
            "require_placeholder_signature": policy.require_placeholder_signature,
        },
        "verification": _serialize_verification(verification),
        "audit_event": event,
    }


@router.get("/admin/operations/plugin-supply-chain/dependency-verifications")
async def list_dependency_verifications(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(PluginDependencyVerification)
            .where(PluginDependencyVerification.client_id == client_id)
            .order_by(PluginDependencyVerification.created_at.desc())
        )
    ).scalars().all()
    return [_serialize_verification(item) for item in rows]


@router.post("/admin/operations/plugin-supply-chain/provenance/{provenance_id}/lineage")
async def create_lineage(
    provenance_id: str,
    request: LineageRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    provenance = await _get_provenance(db, provenance_id, request.client_id)
    lineage = LINEAGE_SERVICE.create_lineage(provenance, request.parent_artifact_hash)
    verification = LINEAGE_SERVICE.verify_lineage(lineage, provenance)
    db.add(lineage)
    event = build_plugin_supply_chain_audit_event("lineage_verified", str(request.client_id), {"provenance_id": provenance.id, "lineage_id": lineage.id})
    await db.commit()
    return {"lineage": _serialize_lineage(lineage), "verification": verification, "audit_event": event}


@router.get("/admin/operations/plugin-supply-chain/lineage")
async def list_lineage(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(PluginArtifactLineage)
            .where(PluginArtifactLineage.client_id == client_id)
            .order_by(PluginArtifactLineage.created_at.desc())
        )
    ).scalars().all()
    return [_serialize_lineage(item) for item in rows]


@router.post("/admin/operations/plugin-supply-chain/provenance/{provenance_id}/replay-verify")
async def replay_verify(
    provenance_id: str,
    request: ReplayRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    provenance = await _get_provenance(db, provenance_id, request.client_id)
    return {"replay_verification": REPLAY_VERIFIER.verify_provenance(provenance)}


@router.post("/admin/operations/plugin-supply-chain/provenance/{provenance_id}/sign-placeholder")
async def create_signature_placeholder(
    provenance_id: str,
    request: SignatureRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    provenance = await _get_provenance(db, provenance_id, request.client_id)
    if request.signature_status not in PLUGIN_SIGNATURE_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported signature status")
    logical_payload = {
        "client_id": str(request.client_id),
        "provenance_record_id": provenance.id,
        "signature_scope": request.signature_scope,
        "signature_status": request.signature_status,
    }
    signature = PluginSignedArtifactPlaceholder(
        id=sha256_hex({"kind": "plugin_signed_artifact_placeholder_id", **logical_payload}),
        client_id=request.client_id,
        provenance_record_id=provenance.id,
        signature_placeholder=f"placeholder-signature:{request.signature_scope}:{provenance.provenance_hash[:16]}",
        signature_scope=request.signature_scope,
        signature_status=request.signature_status,
        immutable_hash=sha256_hex({"kind": "plugin_signed_artifact_placeholder_immutable", **logical_payload}),
    )
    db.add(signature)
    await db.commit()
    return {"signature": _serialize_signature(signature)}


@router.post("/admin/operations/plugin-supply-chain/provenance/{provenance_id}/receipt")
async def create_receipt(
    provenance_id: str,
    request: ReceiptRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    provenance = await _get_provenance(db, provenance_id, request.client_id)
    receipt = build_supply_chain_receipt(request.receipt_type, provenance, provenance.provenance_hash)
    db.add(receipt)
    event = build_plugin_supply_chain_audit_event("supply_chain_receipt_created", str(request.client_id), {"provenance_id": provenance.id, "receipt_id": receipt.id})
    await db.commit()
    return {"receipt": _serialize_receipt(receipt), "audit_event": event}


@router.get("/admin/operations/plugin-supply-chain/receipts")
async def list_receipts(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(PluginSupplyChainReceipt)
            .where(PluginSupplyChainReceipt.client_id == client_id)
            .order_by(PluginSupplyChainReceipt.generated_at.desc())
        )
    ).scalars().all()
    return [_serialize_receipt(item) for item in rows]


@router.get("/admin/operations/plugin-supply-chain/dashboard")
async def get_dashboard_summary(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    provenance_count = (
        await db.execute(select(func.count()).select_from(PluginProvenanceRecord).where(PluginProvenanceRecord.client_id == client_id))
    ).scalar_one()
    sbom_count = (
        await db.execute(select(func.count()).select_from(PluginSBOMPlaceholder).where(PluginSBOMPlaceholder.client_id == client_id))
    ).scalar_one()
    verification_count = (
        await db.execute(select(func.count()).select_from(PluginDependencyVerification).where(PluginDependencyVerification.client_id == client_id))
    ).scalar_one()
    lineage_count = (
        await db.execute(select(func.count()).select_from(PluginArtifactLineage).where(PluginArtifactLineage.client_id == client_id))
    ).scalar_one()
    signature_count = (
        await db.execute(select(func.count()).select_from(PluginSignedArtifactPlaceholder).where(PluginSignedArtifactPlaceholder.client_id == client_id))
    ).scalar_one()
    receipt_count = (
        await db.execute(select(func.count()).select_from(PluginSupplyChainReceipt).where(PluginSupplyChainReceipt.client_id == client_id))
    ).scalar_one()
    return {
        "section": "Plugin Supply-Chain Provenance & SBOM Placeholder Framework",
        "provenance_records": provenance_count,
        "sbom_placeholders": sbom_count,
        "dependency_verification": verification_count,
        "lineage_verification": lineage_count,
        "placeholder_signatures": signature_count,
        "receipts": receipt_count,
        "replay_safe": True,
        "reproducible_build": True,
        "warnings": [
            "placeholder SBOM only",
            "no real artifact signing",
            "offline-first provenance only",
        ],
    }
