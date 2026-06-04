# Owner: platform-ops
import json
from typing import Any
from uuid import UUID

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.reproducible_builds import (
    ARTIFACT_VERIFICATION_STATUSES,
    REPLAY_STATUSES,
    REPRODUCIBILITY_STATUSES,
    REPRODUCIBLE_BUILD_SCOPES,
    ArtifactReplayVerification,
    ArtifactVerificationRecord,
    BuildEnvironmentConstraint,
    ReproducibilityVerificationResult,
    ReproducibleBuildManifest,
    ReproducibleBuildReceipt,
    SourceArtifactLineage,
)
from app.services.operations.reproducible_builds.artifact_verification import (
    ArtifactVerificationService,
)
from app.services.operations.reproducible_builds.audit_events import (
    build_reproducible_build_audit_event,
)
from app.services.operations.reproducible_builds.build_environment_policy import (
    BuildEnvironmentPolicyService,
)
from app.services.operations.reproducible_builds.hash_utils import sha256_hex
from app.services.operations.reproducible_builds.lineage_service import SourceArtifactLineageService
from app.services.operations.reproducible_builds.provenance_integration import (
    ReproducibleBuildProvenanceIntegration,
)
from app.services.operations.reproducible_builds.receipts import (
    build_artifact_receipt,
    build_lineage_receipt,
    build_manifest_receipt,
    build_reproducibility_receipt,
)
from app.services.operations.reproducible_builds.replay_verifier import ArtifactReplayVerifier
from app.services.operations.reproducible_builds.reproducible_build_service import (
    ReproducibleBuildService,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

BUILD_SERVICE = ReproducibleBuildService()
ARTIFACT_SERVICE = ArtifactVerificationService()
LINEAGE_SERVICE = SourceArtifactLineageService()
ENVIRONMENT_SERVICE = BuildEnvironmentPolicyService()
REPLAY_VERIFIER = ArtifactReplayVerifier()
PROVENANCE_INTEGRATION = ReproducibleBuildProvenanceIntegration()


class BuildManifestCreateRequest(BaseModel):
    client_id: UUID
    build_name: str
    build_scope: str
    source_reference: str
    deterministic_version: str = "v1"
    build_environment_hash: str
    reproducibility_status: str = "proposed"
    replay_safe: bool = True


class BuildManifestActionRequest(BaseModel):
    client_id: UUID


class ArtifactVerificationRequest(BaseModel):
    client_id: UUID
    build_manifest_id: str
    artifact_name: str
    artifact_version: str
    artifact_payload: dict[str, Any] = Field(default_factory=dict)
    expected_hash: str | None = None


class LineageVerificationRequest(BaseModel):
    client_id: UUID
    build_manifest_id: str
    source_hash: str
    artifact_hash: str


class ReplayVerificationRequest(BaseModel):
    client_id: UUID
    build_manifest_id: str
    artifact_verification_id: str | None = None
    lineage_id: str | None = None


class EnvironmentValidationRequest(BaseModel):
    client_id: UUID
    constraint_name: str
    constraint_scope: str
    required_determinism: bool = True
    offline_only: bool = True
    external_network_allowed: bool = False
    external_dependency_resolution_allowed: bool = False
    blocked_markers: list[str] = Field(default_factory=list)


class ReceiptRequest(BaseModel):
    client_id: UUID
    receipt_type: str = "build_manifest_receipt"


def _serialize_manifest(item: ReproducibleBuildManifest) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "build_name": item.build_name,
        "build_scope": item.build_scope,
        "source_reference": item.source_reference,
        "deterministic_version": item.deterministic_version,
        "build_environment_hash": item.build_environment_hash,
        "build_manifest_hash": item.build_manifest_hash,
        "reproducibility_status": item.reproducibility_status,
        "replay_safe": item.replay_safe,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_artifact(item: ArtifactVerificationRecord) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "build_manifest_id": item.build_manifest_id,
        "artifact_name": item.artifact_name,
        "artifact_version": item.artifact_version,
        "artifact_hash": item.artifact_hash,
        "verification_status": item.verification_status,
        "replay_verified": item.replay_verified,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_lineage(item: SourceArtifactLineage) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "build_manifest_id": item.build_manifest_id,
        "source_hash": item.source_hash,
        "artifact_hash": item.artifact_hash,
        "lineage_hash": item.lineage_hash,
        "replay_verifiable": item.replay_verifiable,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_constraint(item: BuildEnvironmentConstraint) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "constraint_name": item.constraint_name,
        "constraint_scope": item.constraint_scope,
        "required_determinism": item.required_determinism,
        "offline_only": item.offline_only,
        "external_network_allowed": item.external_network_allowed,
        "external_dependency_resolution_allowed": item.external_dependency_resolution_allowed,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_verification_result(item: ReproducibilityVerificationResult) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "build_manifest_id": item.build_manifest_id,
        "verification_type": item.verification_type,
        "verification_status": item.verification_status,
        "replay_safe": item.replay_safe,
        "reproducibility_summary": json.loads(item.reproducibility_summary),
        "immutable_hash": item.immutable_hash,
    }


def _serialize_replay(item: ArtifactReplayVerification) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "artifact_verification_id": item.artifact_verification_id,
        "replay_hash": item.replay_hash,
        "replay_status": item.replay_status,
        "deterministic_summary": item.deterministic_summary,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_receipt(item: ReproducibleBuildReceipt) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "build_manifest_id": item.build_manifest_id,
        "receipt_type": item.receipt_type,
        "payload_hash": item.payload_hash,
        "immutable_hash": item.immutable_hash,
        "signature": item.signature,
    }


async def _get_manifest(db: AsyncSession, manifest_id: str, client_id: UUID) -> ReproducibleBuildManifest:
    manifest = (
        await db.execute(
            select(ReproducibleBuildManifest).where(
                ReproducibleBuildManifest.id == manifest_id,
                ReproducibleBuildManifest.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not manifest:
        raise HTTPException(status_code=404, detail="Build manifest not found")
    return manifest


async def _get_artifact_verification(db: AsyncSession, artifact_verification_id: str, client_id: UUID) -> ArtifactVerificationRecord:
    record = (
        await db.execute(
            select(ArtifactVerificationRecord).where(
                ArtifactVerificationRecord.id == artifact_verification_id,
                ArtifactVerificationRecord.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Artifact verification not found")
    return record


async def _get_lineage(db: AsyncSession, lineage_id: str, client_id: UUID) -> SourceArtifactLineage:
    lineage = (
        await db.execute(
            select(SourceArtifactLineage).where(
                SourceArtifactLineage.id == lineage_id,
                SourceArtifactLineage.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not lineage:
        raise HTTPException(status_code=404, detail="Lineage record not found")
    return lineage


@router.post("/admin/operations/reproducible-builds/manifests")
async def create_build_manifest(
    request: BuildManifestCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if request.build_scope not in REPRODUCIBLE_BUILD_SCOPES:
        raise HTTPException(status_code=400, detail="Unsupported build scope")
    if request.reproducibility_status not in REPRODUCIBILITY_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported reproducibility status")
    if not request.replay_safe:
        raise HTTPException(status_code=400, detail="replay_safe must be true")
    manifest = BUILD_SERVICE.create_build_manifest(request.model_dump())
    db.add(manifest)
    await db.commit()
    return {
        "manifest": _serialize_manifest(manifest),
        "explanation": BUILD_SERVICE.explain_build_manifest(manifest),
        "audit_event": build_reproducible_build_audit_event(
            "reproducible_build_manifest_created",
            str(request.client_id),
            {"manifest_id": manifest.id, "build_name": manifest.build_name},
        ),
    }


@router.get("/admin/operations/reproducible-builds/manifests")
async def list_build_manifests(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(ReproducibleBuildManifest)
            .where(ReproducibleBuildManifest.client_id == client_id)
            .order_by(ReproducibleBuildManifest.created_at.desc())
        )
    ).scalars().all()
    return [_serialize_manifest(item) for item in rows]


@router.get("/admin/operations/reproducible-builds/manifests/{manifest_id}")
async def get_build_manifest(
    manifest_id: str,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    manifest = await _get_manifest(db, manifest_id, client_id)
    return {
        "manifest": _serialize_manifest(manifest),
        "explanation": BUILD_SERVICE.explain_build_manifest(manifest),
        "integration": PROVENANCE_INTEGRATION.explain_integration(manifest),
    }


@router.post("/admin/operations/reproducible-builds/manifests/{manifest_id}/verify")
async def verify_build_manifest(
    manifest_id: str,
    request: BuildManifestActionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    manifest = await _get_manifest(db, manifest_id, request.client_id)
    verification = BUILD_SERVICE.validate_build_manifest(manifest)
    integration = PROVENANCE_INTEGRATION.validate_supply_chain_alignment(manifest)
    verification_result = ReproducibilityVerificationResult(
        id=sha256_hex({"kind": "reproducibility_verification_result_id", "manifest_id": manifest.id, "verification_type": "hash_replay"}),
        client_id=manifest.client_id,
        build_manifest_id=manifest.id,
        verification_type="hash_replay",
        verification_status="passed" if verification["valid"] else "blocked",
        replay_safe=verification["replay_safe"],
        reproducibility_summary=json.dumps({"manifest_verification": verification, "supply_chain_alignment": integration}, sort_keys=True),
        immutable_hash=sha256_hex({"kind": "reproducibility_verification_result_immutable", "manifest_id": manifest.id, "status": verification["reproducibility_status"]}),
    )
    db.add(verification_result)
    await db.commit()
    return {
        "manifest": _serialize_manifest(manifest),
        "verification_result": _serialize_verification_result(verification_result),
        "audit_event": build_reproducible_build_audit_event(
            "reproducibility_verification_completed",
            str(request.client_id),
            {"manifest_id": manifest.id, "verification_type": "hash_replay"},
        ),
    }


@router.post("/admin/operations/reproducible-builds/artifacts/verify")
async def verify_artifact(
    request: ArtifactVerificationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    manifest = await _get_manifest(db, request.build_manifest_id, request.client_id)
    record = ARTIFACT_SERVICE.verify_artifact(manifest, request.model_dump())
    replay = ARTIFACT_SERVICE.validate_artifact_replay(record)
    if record.verification_status not in ARTIFACT_VERIFICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported artifact verification status")
    if replay.replay_status not in REPLAY_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported replay status")
    db.add(record)
    db.add(replay)
    await db.commit()
    return {
        "artifact_verification": _serialize_artifact(record),
        "artifact_replay": _serialize_replay(replay),
        "explanation": ARTIFACT_SERVICE.explain_artifact_verification(record, replay),
        "audit_event": build_reproducible_build_audit_event(
            "artifact_verified",
            str(request.client_id),
            {"manifest_id": manifest.id, "artifact_verification_id": record.id},
        ),
    }


@router.post("/admin/operations/reproducible-builds/lineage/verify")
async def verify_lineage(
    request: LineageVerificationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    manifest = await _get_manifest(db, request.build_manifest_id, request.client_id)
    lineage = LINEAGE_SERVICE.create_lineage(manifest, request.source_hash, request.artifact_hash)
    verification = LINEAGE_SERVICE.verify_lineage(lineage)
    integrity = LINEAGE_SERVICE.validate_lineage_integrity(lineage, request.artifact_hash)
    db.add(lineage)
    await db.commit()
    return {
        "lineage": _serialize_lineage(lineage),
        "verification": verification,
        "integrity": integrity,
        "explanation": LINEAGE_SERVICE.explain_lineage(lineage),
        "audit_event": build_reproducible_build_audit_event(
            "lineage_verified",
            str(request.client_id),
            {"manifest_id": manifest.id, "lineage_id": lineage.id},
        ),
    }


@router.post("/admin/operations/reproducible-builds/replay/verify")
async def replay_verify(
    request: ReplayVerificationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    manifest = await _get_manifest(db, request.build_manifest_id, request.client_id)
    response: dict[str, Any] = {"manifest_replay": REPLAY_VERIFIER.replay_build_manifest(manifest)}
    if request.artifact_verification_id:
        artifact = await _get_artifact_verification(db, request.artifact_verification_id, request.client_id)
        response["artifact_replay"] = REPLAY_VERIFIER.replay_artifact(artifact)
    if request.lineage_id:
        lineage = await _get_lineage(db, request.lineage_id, request.client_id)
        response["lineage_replay"] = REPLAY_VERIFIER.replay_lineage(lineage)
    response["audit_event"] = build_reproducible_build_audit_event(
        "replay_verification_completed",
        str(request.client_id),
        {"manifest_id": manifest.id, "artifact_verification_id": request.artifact_verification_id, "lineage_id": request.lineage_id},
    )
    return response


@router.post("/admin/operations/reproducible-builds/environment/validate")
async def validate_environment(
    request: EnvironmentValidationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    constraint = ENVIRONMENT_SERVICE.validate_environment_constraints(request.model_dump())
    offline = ENVIRONMENT_SERVICE.enforce_offline_constraints(constraint)
    determinism = ENVIRONMENT_SERVICE.enforce_determinism_constraints(constraint, {"blocked_markers": request.blocked_markers})
    db.add(constraint)
    await db.commit()
    return {
        "constraint": _serialize_constraint(constraint),
        "offline_validation": offline,
        "determinism_validation": determinism,
        "explanation": ENVIRONMENT_SERVICE.explain_constraints(constraint),
        "audit_event": build_reproducible_build_audit_event(
            "build_environment_validated",
            str(request.client_id),
            {"constraint_id": constraint.id, "constraint_name": constraint.constraint_name},
        ),
    }


@router.post("/admin/operations/reproducible-builds/manifests/{manifest_id}/receipt")
async def create_receipt(
    manifest_id: str,
    request: ReceiptRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    manifest = await _get_manifest(db, manifest_id, request.client_id)
    verification_result = (
        await db.execute(
            select(ReproducibilityVerificationResult)
            .where(
                ReproducibilityVerificationResult.build_manifest_id == manifest.id,
                ReproducibilityVerificationResult.client_id == request.client_id,
            )
            .order_by(ReproducibilityVerificationResult.created_at.desc())
        )
    ).scalars().first()
    artifact = (
        await db.execute(
            select(ArtifactVerificationRecord)
            .where(
                ArtifactVerificationRecord.build_manifest_id == manifest.id,
                ArtifactVerificationRecord.client_id == request.client_id,
            )
            .order_by(ArtifactVerificationRecord.created_at.desc())
        )
    ).scalars().first()
    lineage = (
        await db.execute(
            select(SourceArtifactLineage)
            .where(
                SourceArtifactLineage.build_manifest_id == manifest.id,
                SourceArtifactLineage.client_id == request.client_id,
            )
            .order_by(SourceArtifactLineage.created_at.desc())
        )
    ).scalars().first()

    if request.receipt_type == "artifact_verification_receipt":
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact verification not found")
        receipt = build_artifact_receipt(manifest, artifact)
    elif request.receipt_type == "lineage_receipt":
        if not lineage:
            raise HTTPException(status_code=404, detail="Lineage record not found")
        receipt = build_lineage_receipt(manifest, lineage)
    elif request.receipt_type == "reproducibility_receipt":
        if not verification_result:
            raise HTTPException(status_code=404, detail="Verification result not found")
        receipt = build_reproducibility_receipt(manifest, verification_result)
    else:
        receipt = build_manifest_receipt(manifest)

    db.add(receipt)
    await db.commit()
    return {
        "receipt": _serialize_receipt(receipt),
        "audit_event": build_reproducible_build_audit_event(
            "reproducible_build_receipt_created",
            str(request.client_id),
            {"manifest_id": manifest.id, "receipt_id": receipt.id, "receipt_type": receipt.receipt_type},
        ),
    }


@router.get("/admin/operations/reproducible-builds/dashboard")
async def reproducible_build_dashboard(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    manifest_count = (
        await db.execute(select(func.count()).select_from(ReproducibleBuildManifest).where(ReproducibleBuildManifest.client_id == client_id))
    ).scalar_one()
    reproducible_count = (
        await db.execute(
            select(func.count()).select_from(ReproducibleBuildManifest).where(
                ReproducibleBuildManifest.client_id == client_id,
                ReproducibleBuildManifest.reproducibility_status == "reproducible",
            )
        )
    ).scalar_one()
    warning_count = (
        await db.execute(
            select(func.count()).select_from(ReproducibleBuildManifest).where(
                ReproducibleBuildManifest.client_id == client_id,
                ReproducibleBuildManifest.reproducibility_status == "warning",
            )
        )
    ).scalar_one()
    blocked_count = (
        await db.execute(
            select(func.count()).select_from(ReproducibleBuildManifest).where(
                ReproducibleBuildManifest.client_id == client_id,
                ReproducibleBuildManifest.reproducibility_status == "blocked",
            )
        )
    ).scalar_one()
    artifact_count = (
        await db.execute(select(func.count()).select_from(ArtifactVerificationRecord).where(ArtifactVerificationRecord.client_id == client_id))
    ).scalar_one()
    replay_count = (
        await db.execute(select(func.count()).select_from(ArtifactReplayVerification).where(ArtifactReplayVerification.client_id == client_id))
    ).scalar_one()
    lineage_count = (
        await db.execute(select(func.count()).select_from(SourceArtifactLineage).where(SourceArtifactLineage.client_id == client_id))
    ).scalar_one()
    environment_count = (
        await db.execute(select(func.count()).select_from(BuildEnvironmentConstraint).where(BuildEnvironmentConstraint.client_id == client_id))
    ).scalar_one()
    receipt_count = (
        await db.execute(select(func.count()).select_from(ReproducibleBuildReceipt).where(ReproducibleBuildReceipt.client_id == client_id))
    ).scalar_one()
    return {
        "section": "Reproducible Build & Artifact Verification Framework",
        "total_build_manifests": manifest_count,
        "reproducible_manifests": reproducible_count,
        "warning_manifests": warning_count,
        "blocked_manifests": blocked_count,
        "artifact_verification_status": artifact_count,
        "replay_verification_status": replay_count,
        "lineage_verification_status": lineage_count,
        "build_environment_validation": environment_count,
        "replay_safe_status": True,
        "receipts_available": receipt_count,
        "warnings": [
            "deterministic verification only",
            "no real external build execution",
            "offline-first reproducible build framework",
        ],
    }
