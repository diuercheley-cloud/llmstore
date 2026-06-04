# Owner: platform-ops
from typing import Any, Optional
from uuid import UUID

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.federation_sync import (
    BUNDLE_TYPES,
    CONFLICT_TYPES,
    ENVIRONMENT_TYPES,
    RESOLUTION_STRATEGIES,
    TRUST_LEVELS,
    FederationConflictResolution,
    FederationLineageLink,
    FederationSynchronizationBundle,
    FederationSynchronizationReceipt,
    FederationSynchronizationSession,
    SovereignFederationEnvironment,
)
from app.services.operations.federation_sync.audit_events import build_federation_sync_audit_event
from app.services.operations.federation_sync.conflict_resolution import (
    FederationConflictResolutionService,
)
from app.services.operations.federation_sync.environment_registry import (
    SovereignFederationEnvironmentRegistry,
)
from app.services.operations.federation_sync.hash_utils import sha256_hex
from app.services.operations.federation_sync.receipts import (
    build_sync_session_receipt,
)
from app.services.operations.federation_sync.replay_verifier import FederationReplayVerifier
from app.services.operations.federation_sync.synchronization_protocol import (
    SovereignFederationSynchronizationProtocol,
)
from app.services.operations.federation_sync.trust_negotiation import (
    FederationTrustNegotiationService,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

REGISTRY = SovereignFederationEnvironmentRegistry()
PROTOCOL = SovereignFederationSynchronizationProtocol()
NEGOTIATION_SERVICE = FederationTrustNegotiationService()
CONFLICT_SERVICE = FederationConflictResolutionService()
REPLAY_VERIFIER = FederationReplayVerifier()


class EnvironmentCreateRequest(BaseModel):
    client_id: UUID
    environment_name: str
    environment_type: str
    federation_scope: str
    trust_level: str = "restricted"
    offline_only: bool = True
    deterministic_version: str = "v1"


class SessionCreateRequest(BaseModel):
    client_id: UUID
    source_environment_id: str
    target_environment_id: str


class BundleExportRequest(BaseModel):
    client_id: UUID
    session_id: str
    bundle_name: str
    bundle_type: str
    parent_bundle_hash: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class BundleImportRequest(BaseModel):
    client_id: UUID
    session_id: str
    bundle_payload: dict[str, Any]


class VerificationRequest(BaseModel):
    client_id: UUID


class TrustNegotiationRequest(BaseModel):
    client_id: UUID
    source_environment_id: str
    target_environment_id: str


class ConflictResolutionRequest(BaseModel):
    client_id: UUID
    session_id: str
    source_bundle_id: str
    target_bundle_id: str
    conflict_type: str
    strategy: str


class ReceiptRequest(BaseModel):
    client_id: UUID


def _serialize_environment(item: SovereignFederationEnvironment) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "environment_name": item.environment_name,
        "environment_type": item.environment_type,
        "federation_scope": item.federation_scope,
        "trust_level": item.trust_level,
        "offline_only": item.offline_only,
        "deterministic_version": item.deterministic_version,
        "environment_hash": item.environment_hash,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_session(item: FederationSynchronizationSession) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "source_environment_id": item.source_environment_id,
        "target_environment_id": item.target_environment_id,
        "sync_scope": item.sync_scope,
        "sync_status": item.sync_status,
        "replay_verifiable": item.replay_verifiable,
        "offline_verifiable": item.offline_verifiable,
        "lineage_verified": item.lineage_verified,
        "deterministic_version": item.deterministic_version,
        "session_hash": item.session_hash,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_bundle(item: FederationSynchronizationBundle) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "session_id": item.session_id,
        "bundle_name": item.bundle_name,
        "bundle_type": item.bundle_type,
        "bundle_hash": item.bundle_hash,
        "lineage_hash": item.lineage_hash,
        "parent_bundle_hash": item.parent_bundle_hash,
        "replay_hash": item.replay_hash,
        "bundle_status": item.bundle_status,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_conflict(item: FederationConflictResolution) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "session_id": item.session_id,
        "conflict_type": item.conflict_type,
        "resolution_strategy": item.resolution_strategy,
        "resolution_status": item.resolution_status,
        "replay_safe": item.replay_safe,
        "immutable_hash": item.immutable_hash,
    }


async def _get_environment(db: AsyncSession, environment_id: str, client_id: UUID) -> SovereignFederationEnvironment:
    environment = (
        await db.execute(
            select(SovereignFederationEnvironment).where(
                SovereignFederationEnvironment.id == environment_id,
                SovereignFederationEnvironment.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    return environment


async def _get_session(db: AsyncSession, session_id: str, client_id: UUID) -> FederationSynchronizationSession:
    item = (
        await db.execute(
            select(FederationSynchronizationSession).where(
                FederationSynchronizationSession.id == session_id,
                FederationSynchronizationSession.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Synchronization session not found")
    return item


async def _get_bundle(db: AsyncSession, bundle_id: str, client_id: UUID) -> FederationSynchronizationBundle:
    item = (
        await db.execute(
            select(FederationSynchronizationBundle).where(
                FederationSynchronizationBundle.id == bundle_id,
                FederationSynchronizationBundle.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return item


@router.post("/admin/operations/federation/environments")
async def register_environment(
    request: EnvironmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if request.environment_type not in ENVIRONMENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported environment type")
    if request.trust_level not in TRUST_LEVELS:
        raise HTTPException(status_code=400, detail="Unsupported trust level")
    environment = REGISTRY.register_environment(request.model_dump())
    db.add(environment)
    await db.commit()
    return {
        "environment": _serialize_environment(environment),
        "verification": REGISTRY.verify_environment(environment),
        "audit_event": build_federation_sync_audit_event(
            "federation_environment_registered",
            str(environment.client_id),
            {"environment_id": environment.id, "environment_name": environment.environment_name},
        ),
    }


@router.get("/admin/operations/federation/environments")
async def list_environments(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(SovereignFederationEnvironment)
            .where(SovereignFederationEnvironment.client_id == client_id)
            .order_by(SovereignFederationEnvironment.created_at.desc())
        )
    ).scalars().all()
    return [_serialize_environment(item) for item in rows]


@router.post("/admin/operations/federation/sessions")
async def create_sync_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    source = await _get_environment(db, request.source_environment_id, request.client_id)
    target = await _get_environment(db, request.target_environment_id, request.client_id)
    if source.client_id != target.client_id:
        raise HTTPException(status_code=403, detail="Cross-tenant synchronization is blocked")
    session = PROTOCOL.create_sync_session(source, target)
    db.add(session)
    await db.commit()
    return {
        "session": _serialize_session(session),
        "audit_event": build_federation_sync_audit_event(
            "federation_sync_session_created",
            str(session.client_id),
            {"session_id": session.id, "sync_scope": session.sync_scope},
        ),
    }


@router.get("/admin/operations/federation/sessions")
async def list_sessions(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(FederationSynchronizationSession)
            .where(FederationSynchronizationSession.client_id == client_id)
            .order_by(FederationSynchronizationSession.created_at.desc())
        )
    ).scalars().all()
    return [_serialize_session(item) for item in rows]


@router.get("/admin/operations/federation/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    session = await _get_session(db, session_id, client_id)
    bundles_count = await db.scalar(
        select(func.count()).select_from(FederationSynchronizationBundle).where(
            FederationSynchronizationBundle.client_id == client_id,
            FederationSynchronizationBundle.session_id == session_id,
        )
    )
    conflicts_count = await db.scalar(
        select(func.count()).select_from(FederationConflictResolution).where(
            FederationConflictResolution.client_id == client_id,
            FederationConflictResolution.session_id == session_id,
        )
    )
    return {
        "session": _serialize_session(session),
        "explanation": PROTOCOL.explain_session(session),
        "bundle_count": bundles_count or 0,
        "conflict_count": conflicts_count or 0,
    }


@router.post("/admin/operations/federation/bundles/export")
async def export_bundle(
    request: BundleExportRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if request.bundle_type not in BUNDLE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported bundle type")
    session = await _get_session(db, request.session_id, request.client_id)
    bundle = PROTOCOL.export_bundle(session, request.model_dump())
    db.add(bundle)
    db.add(
        FederationLineageLink(
            id=sha256_hex({"kind": "federation_lineage_link_id", "bundle_id": bundle.id}),
            client_id=bundle.client_id,
            bundle_id=bundle.id,
            parent_bundle_hash=bundle.parent_bundle_hash,
            lineage_hash=bundle.lineage_hash,
            replay_verifiable=True,
            immutable_hash=sha256_hex({"kind": "federation_lineage_link_immutable", "bundle_id": bundle.id, "lineage_hash": bundle.lineage_hash}),
        )
    )
    await db.commit()
    payload = {
        "bundle_id": bundle.id,
        "session_id": session.id,
        "bundle_hash": bundle.bundle_hash,
        "lineage_hash": bundle.lineage_hash,
        "parent_bundle_hash": bundle.parent_bundle_hash,
        "replay_hash": bundle.replay_hash,
        "bundle_type": bundle.bundle_type,
        "bundle_name": bundle.bundle_name,
    }
    return {
        "bundle": _serialize_bundle(bundle),
        "payload": payload,
        "audit_event": build_federation_sync_audit_event(
            "federation_bundle_exported",
            str(bundle.client_id),
            {"bundle_id": bundle.id, "session_id": bundle.session_id},
        ),
    }


@router.post("/admin/operations/federation/bundles/import")
async def import_bundle(
    request: BundleImportRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    session = await _get_session(db, request.session_id, request.client_id)
    raw = request.bundle_payload
    existing = (
        await db.execute(
            select(FederationSynchronizationBundle).where(
                FederationSynchronizationBundle.id == raw["bundle_id"],
                FederationSynchronizationBundle.client_id == request.client_id,
                FederationSynchronizationBundle.session_id == session.id,
            )
        )
    ).scalar_one_or_none()
    bundle = existing or FederationSynchronizationBundle(
        id=raw["bundle_id"],
        client_id=request.client_id,
        session_id=session.id,
        bundle_name=raw["bundle_name"],
        bundle_type=raw["bundle_type"],
        bundle_hash=raw["bundle_hash"],
        lineage_hash=raw["lineage_hash"],
        parent_bundle_hash=raw.get("parent_bundle_hash"),
        replay_hash=raw["replay_hash"],
        bundle_status="created",
        immutable_hash=sha256_hex({"kind": "federation_bundle_import_immutable", "bundle_hash": raw["bundle_hash"], "session_id": session.id}),
    )
    bundle._logical_payload = {
        "client_id": str(request.client_id),
        "session_id": session.id,
        "bundle_name": bundle.bundle_name,
        "bundle_type": bundle.bundle_type,
        "parent_bundle_hash": bundle.parent_bundle_hash,
        "payload": {},
        "deterministic_version": session.deterministic_version,
    }
    imported = PROTOCOL.import_bundle(session, bundle)
    if existing is None:
        db.add(imported)
    await db.commit()
    return {
        "bundle": _serialize_bundle(imported),
        "verification": PROTOCOL.verify_bundle(imported),
        "audit_event": build_federation_sync_audit_event(
            "federation_bundle_imported",
            str(imported.client_id),
            {"bundle_id": imported.id, "session_id": imported.session_id},
        ),
    }


@router.post("/admin/operations/federation/bundles/{bundle_id}/verify")
async def verify_bundle(
    bundle_id: str,
    request: VerificationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    bundle = await _get_bundle(db, bundle_id, request.client_id)
    session = await _get_session(db, bundle.session_id, request.client_id)
    replay = REPLAY_VERIFIER.replay_bundle(bundle)
    lineage_rows = (
        await db.execute(
            select(FederationLineageLink).where(
                FederationLineageLink.client_id == request.client_id,
                FederationLineageLink.bundle_id == bundle.id,
            )
        )
    ).scalars().all()
    lineage = REPLAY_VERIFIER.validate_lineage(lineage_rows)
    verified = replay["match"] and lineage["valid"]
    bundle.bundle_status = "verified" if verified else "conflicted"
    session.lineage_verified = lineage["valid"]
    session.replay_verifiable = replay["match"]
    session.sync_status = "verified" if verified else "conflicted"
    await db.commit()
    return {
        "bundle": _serialize_bundle(bundle),
        "verification": {
            "verified": verified,
            "replay_verified": replay["match"],
            "lineage_verified": lineage["valid"],
            "offline_verified": True,
        },
        "audit_event": build_federation_sync_audit_event(
            "federation_bundle_verified",
            str(bundle.client_id),
            {"bundle_id": bundle.id, "session_id": bundle.session_id},
        ),
    }


@router.post("/admin/operations/federation/trust-negotiate")
async def trust_negotiate(
    request: TrustNegotiationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    source = await _get_environment(db, request.source_environment_id, request.client_id)
    target = await _get_environment(db, request.target_environment_id, request.client_id)
    negotiation = NEGOTIATION_SERVICE.negotiate(source, target)
    db.add(negotiation)
    await db.commit()
    return {
        "negotiation": {
            "id": negotiation.id,
            "client_id": str(negotiation.client_id),
            "negotiation_status": negotiation.negotiation_status,
            "required_trust_level": negotiation.required_trust_level,
            "negotiated_trust_level": negotiation.negotiated_trust_level,
        },
        "validation": NEGOTIATION_SERVICE.validate_negotiation(negotiation),
        "audit_event": build_federation_sync_audit_event(
            "federation_trust_negotiated",
            str(negotiation.client_id),
            {"negotiation_id": negotiation.id, "status": negotiation.negotiation_status},
        ),
    }


@router.post("/admin/operations/federation/conflicts/resolve")
async def resolve_conflict(
    request: ConflictResolutionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if request.conflict_type not in CONFLICT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported conflict type")
    if request.strategy not in RESOLUTION_STRATEGIES:
        raise HTTPException(status_code=400, detail="Unsupported resolution strategy")
    session = await _get_session(db, request.session_id, request.client_id)
    source = await _get_bundle(db, request.source_bundle_id, request.client_id)
    target = await _get_bundle(db, request.target_bundle_id, request.client_id)
    conflicts = CONFLICT_SERVICE.detect_conflicts(source, target)
    matched = next((item for item in conflicts if item["conflict_type"] == request.conflict_type), None)
    if not matched:
        raise HTTPException(status_code=400, detail="Conflict not detected for the provided bundles")
    resolution = CONFLICT_SERVICE.resolve_conflict(
        {
            **matched,
            "client_id": request.client_id,
            "session_id": session.id,
        },
        request.strategy,
    )
    if request.strategy == "manual_review_required":
        session.sync_status = "conflicted"
    db.add(resolution)
    await db.commit()
    return {
        "resolution": _serialize_conflict(resolution),
        "validation": CONFLICT_SERVICE.validate_resolution(resolution),
        "audit_event": build_federation_sync_audit_event(
            "federation_conflict_resolved",
            str(request.client_id),
            {"session_id": session.id, "conflict_type": resolution.conflict_type},
        ),
    }


@router.get("/admin/operations/federation/lineage/{bundle_id}")
async def get_lineage(
    bundle_id: str,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    await _get_bundle(db, bundle_id, client_id)
    links = (
        await db.execute(
            select(FederationLineageLink)
            .where(FederationLineageLink.client_id == client_id, FederationLineageLink.bundle_id == bundle_id)
            .order_by(FederationLineageLink.created_at.asc())
        )
    ).scalars().all()
    return {
        "bundle_id": bundle_id,
        "lineage_chain": [
            {
                "id": item.id,
                "parent_bundle_hash": item.parent_bundle_hash,
                "lineage_hash": item.lineage_hash,
                "replay_verifiable": item.replay_verifiable,
            }
            for item in links
        ],
        "lineage_status": REPLAY_VERIFIER.validate_lineage(links),
    }


@router.post("/admin/operations/federation/sessions/{session_id}/receipt")
async def generate_session_receipt(
    session_id: str,
    request: ReceiptRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    session = await _get_session(db, session_id, request.client_id)
    receipt_payload = build_sync_session_receipt(session)
    receipt = FederationSynchronizationReceipt(
        id=sha256_hex({"kind": "federation_receipt_id", "session_id": session.id, "payload_hash": receipt_payload["payload_hash"]}),
        client_id=session.client_id,
        session_id=session.id,
        receipt_type=receipt_payload["receipt_type"],
        payload_hash=receipt_payload["payload_hash"],
        immutable_hash=receipt_payload["immutable_hash"],
        signature=receipt_payload["signature"],
    )
    db.add(receipt)
    await db.commit()
    return {
        "receipt": {**receipt_payload, "generated_at": receipt_payload["generated_at"].isoformat()},
        "audit_event": build_federation_sync_audit_event(
            "federation_receipt_created",
            str(session.client_id),
            {"session_id": session.id, "receipt_type": receipt.receipt_type},
        ),
    }
