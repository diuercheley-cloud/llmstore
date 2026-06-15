# Owner: platform-ops
from typing import Any
from uuid import UUID

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.attestation_framework import (
    ATTESTATION_TYPES,
    AttestationFederationBundle,
    AttestationReceipt,
    AttestationTrustPolicy,
    SovereignExecutionAttestation,
)
from app.services.operations.attestation_framework.attestation_service import (
    SovereignExecutionAttestationService,
)
from app.services.operations.attestation_framework.audit_events import build_attestation_audit_event
from app.services.operations.attestation_framework.federation_bundle import (
    AttestationFederationBundleService,
)
from app.services.operations.attestation_framework.hash_utils import sha256_hex
from app.services.operations.attestation_framework.receipts import (
    build_attestation_receipt,
    build_bundle_receipt,
    build_chain_receipt,
    build_verification_receipt,
)
from app.services.operations.attestation_framework.replay_verifier import AttestationReplayVerifier
from app.services.operations.attestation_framework.trust_policy_engine import (
    AttestationTrustPolicyEngine,
)
from app.utils.crypto_signer import sign_payload
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/operations", tags=["operations-attestation"])

ATTESTATION_SERVICE = SovereignExecutionAttestationService()
BUNDLE_SERVICE = AttestationFederationBundleService()
REPLAY_VERIFIER = AttestationReplayVerifier()
TRUST_ENGINE = AttestationTrustPolicyEngine()


class AttestationCreateRequest(BaseModel):
    client_id: UUID
    attestation_type: str
    subject_type: str
    subject_ref: str
    attestation_scope: str = "operations"
    payload: dict[str, Any] = Field(default_factory=dict)
    signature: str = sign_payload("attestation")


class AttestationActionRequest(BaseModel):
    client_id: UUID


class AttestationRevokeRequest(BaseModel):
    client_id: UUID
    reason: str = Field(..., min_length=3)


class BundleCreateRequest(BaseModel):
    client_id: UUID
    attestation_ids: list[str]
    target_environment: str
    bundle_name: str = "attestation-federation-bundle"
    source_environment: str = "offline-source"
    bundle_scope: str = "operations"


class BundleImportRequest(BaseModel):
    client_id: UUID
    bundle_payload: dict[str, Any]


class AttestationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: UUID
    attestation_type: str
    subject_type: str
    subject_ref: str
    attestation_scope: str
    attestation_status: str
    payload_hash: str
    attestation_hash: str
    previous_attestation_hash: str | None
    signature: str
    attestation_chain_position: str
    replay_verifiable: bool
    offline_verifiable: bool
    immutable_hash: str


class BundleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    client_id: UUID
    bundle_name: str
    bundle_scope: str
    bundle_hash: str
    source_environment: str
    target_environment: str
    bundle_status: str
    replay_verifiable: bool
    offline_verifiable: bool
    immutable_hash: str


def _serialize_attestation(attestation: SovereignExecutionAttestation) -> dict[str, Any]:
    return {
        "id": attestation.id,
        "client_id": attestation.client_id,
        "attestation_type": attestation.attestation_type,
        "subject_type": attestation.subject_type,
        "subject_ref": attestation.subject_ref,
        "attestation_scope": attestation.attestation_scope,
        "attestation_status": attestation.attestation_status,
        "payload_hash": attestation.payload_hash,
        "attestation_hash": attestation.attestation_hash,
        "previous_attestation_hash": attestation.previous_attestation_hash,
        "signature": attestation.signature,
        "attestation_chain_position": attestation.attestation_chain_position,
        "replay_verifiable": attestation.replay_verifiable,
        "offline_verifiable": attestation.offline_verifiable,
        "immutable_hash": attestation.immutable_hash,
    }


def _serialize_bundle(bundle: AttestationFederationBundle) -> dict[str, Any]:
    return {
        "id": bundle.id,
        "client_id": bundle.client_id,
        "bundle_name": bundle.bundle_name,
        "bundle_scope": bundle.bundle_scope,
        "bundle_hash": bundle.bundle_hash,
        "source_environment": bundle.source_environment,
        "target_environment": bundle.target_environment,
        "bundle_status": bundle.bundle_status,
        "replay_verifiable": bundle.replay_verifiable,
        "offline_verifiable": bundle.offline_verifiable,
        "immutable_hash": bundle.immutable_hash,
    }


async def _get_attestation_or_404(
    db: AsyncSession, attestation_id: str, client_id: UUID
) -> SovereignExecutionAttestation:
    result = await db.execute(
        select(SovereignExecutionAttestation).where(
            SovereignExecutionAttestation.id == attestation_id,
            SovereignExecutionAttestation.client_id == client_id,
        )
    )
    attestation = result.scalar_one_or_none()
    if not attestation:
        raise HTTPException(status_code=404, detail="Attestation not found")
    return attestation


async def _get_or_create_policy(db: AsyncSession, client_id: UUID) -> AttestationTrustPolicy:
    result = await db.execute(
        select(AttestationTrustPolicy)
        .where(AttestationTrustPolicy.client_id == client_id)
        .order_by(AttestationTrustPolicy.created_at.desc())
    )
    policy = result.scalars().first()
    if policy:
        return policy
    allowed = {"allowed": list(ATTESTATION_TYPES)}
    immutable_hash = sha256_hex(
        {"kind": "attestation_policy", "client_id": str(client_id), "allowed": allowed}
    )
    policy = AttestationTrustPolicy(
        id=sha256_hex(
            {"kind": "attestation_policy_id", "client_id": str(client_id), "policy_name": "default"}
        ),
        client_id=client_id,
        policy_name="default",
        allowed_attestation_types_json=allowed,
        immutable_hash=immutable_hash,
    )
    db.add(policy)
    await db.flush()
    return policy


@router.post("/attestations")
async def create_attestation(
    request: AttestationCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if request.attestation_type not in ATTESTATION_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported attestation type")
    previous_result = await db.execute(
        select(SovereignExecutionAttestation)
        .where(
            SovereignExecutionAttestation.client_id == request.client_id,
            SovereignExecutionAttestation.subject_type == request.subject_type,
            SovereignExecutionAttestation.subject_ref == request.subject_ref,
        )
        .order_by(SovereignExecutionAttestation.created_at.desc())
    )
    previous = previous_result.scalars().first()
    attestation = ATTESTATION_SERVICE.issue_attestation(
        {
            "client_id": request.client_id,
            "subject_type": request.subject_type,
            "subject_ref": request.subject_ref,
            "attestation_scope": request.attestation_scope,
            "payload": request.payload,
            "signature": request.signature,
            "previous_attestation_hash": previous.attestation_hash if previous else None,
            "attestation_chain_position": str(
                (int(previous.attestation_chain_position) + 1) if previous else 1
            ),
            "replay_verifiable": True,
            "offline_verifiable": True,
        },
        request.attestation_type,
    )
    db.add(attestation)
    receipt_payload = build_attestation_receipt(attestation)
    receipt = AttestationReceipt(
        id=sha256_hex(
            {
                "kind": "attestation_receipt_id",
                "attestation_id": attestation.id,
                "payload_hash": receipt_payload["payload_hash"],
            }
        ),
        client_id=attestation.client_id,
        attestation_id=attestation.id,
        receipt_type=receipt_payload["receipt_type"],
        payload_hash=receipt_payload["payload_hash"],
        immutable_hash=receipt_payload["immutable_hash"],
        signature=receipt_payload["signature"],
    )
    db.add(receipt)
    await db.commit()
    serialized = _serialize_attestation(attestation)
    return {
        "attestation": serialized,
        "receipt": {
            **receipt_payload,
            "generated_at": receipt_payload["generated_at"].isoformat(),
        },
        "audit_event": build_attestation_audit_event(
            "attestation_issued", str(attestation.client_id), {"attestation_id": attestation.id}
        ),
    }


@router.get("/attestations")
async def list_attestations(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    result = await db.execute(
        select(SovereignExecutionAttestation)
        .where(SovereignExecutionAttestation.client_id == client_id)
        .order_by(SovereignExecutionAttestation.created_at.desc())
    )
    return [_serialize_attestation(item) for item in result.scalars().all()]


@router.get("/attestations/{attestation_id}")
async def get_attestation(
    attestation_id: str,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    attestation = await _get_attestation_or_404(db, attestation_id, client_id)
    return {
        "attestation": _serialize_attestation(attestation),
        "explanation": ATTESTATION_SERVICE.explain_attestation(attestation),
    }


@router.post("/attestations/{attestation_id}/verify")
async def verify_attestation(
    attestation_id: str,
    request: AttestationActionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    attestation = await _get_attestation_or_404(db, attestation_id, request.client_id)
    verification = ATTESTATION_SERVICE.verify_attestation(attestation)
    policy = await _get_or_create_policy(db, request.client_id)
    chain = ATTESTATION_SERVICE.build_attestation_chain([attestation])
    policy_result = TRUST_ENGINE.evaluate_attestation(attestation, policy)
    replay_result = REPLAY_VERIFIER.replay_attestation(attestation)
    verification.replay_verified = replay_result["match"]
    verification.chain_verified = ATTESTATION_SERVICE.validate_chain_integrity(chain)
    verification.offline_verified = attestation.offline_verifiable
    verification.verification_status = (
        "passed"
        if verification.replay_verified
        and verification.chain_verified
        and verification.offline_verified
        and policy_result["allowed"]
        else "failed"
    )
    verification.immutable_hash = sha256_hex(
        {
            "kind": "verification",
            "attestation_id": attestation.id,
            "status": verification.verification_status,
        }
    )
    attestation.attestation_status = (
        "verified"
        if verification.verification_status == "passed"
        else attestation.attestation_status
    )
    db.add(verification)
    await db.commit()
    verification_receipt = build_verification_receipt(verification)
    return {
        "verification": {
            "id": verification.id,
            "status": verification.verification_status,
            "summary": verification.verification_summary,
            "replay_verified": verification.replay_verified,
            "chain_verified": verification.chain_verified,
            "offline_verified": verification.offline_verified,
        },
        "policy_result": policy_result,
        "verification_receipt": {
            **verification_receipt,
            "generated_at": verification_receipt["generated_at"].isoformat(),
        },
    }


@router.post("/attestations/{attestation_id}/revoke")
async def revoke_attestation(
    attestation_id: str,
    request: AttestationRevokeRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    attestation = await _get_attestation_or_404(db, attestation_id, request.client_id)
    ATTESTATION_SERVICE.revoke_attestation(attestation, request.reason)
    await db.commit()
    return {
        "attestation": _serialize_attestation(attestation),
        "audit_event": build_attestation_audit_event(
            "attestation_revoked",
            str(request.client_id),
            {"attestation_id": attestation.id, "reason": request.reason},
        ),
    }


@router.post("/attestation-bundles")
async def create_attestation_bundle(
    request: BundleCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    result = await db.execute(
        select(SovereignExecutionAttestation).where(
            SovereignExecutionAttestation.client_id == request.client_id,
            SovereignExecutionAttestation.id.in_(request.attestation_ids),
        )
    )
    attestations = result.scalars().all()
    if len(attestations) != len(request.attestation_ids):
        raise HTTPException(status_code=404, detail="One or more attestations were not found")
    bundle, payload = BUNDLE_SERVICE.create_bundle(
        attestations,
        request.target_environment,
        bundle_name=request.bundle_name,
        source_environment=request.source_environment,
        bundle_scope=request.bundle_scope,
    )
    db.add(bundle)
    await db.commit()
    bundle_receipt = build_bundle_receipt(bundle)
    return {
        "bundle": _serialize_bundle(bundle),
        "bundle_receipt": {
            **bundle_receipt,
            "generated_at": bundle_receipt["generated_at"].isoformat(),
        },
        "payload": payload,
    }


@router.get("/attestation-bundles")
async def list_attestation_bundles(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    result = await db.execute(
        select(AttestationFederationBundle)
        .where(AttestationFederationBundle.client_id == client_id)
        .order_by(AttestationFederationBundle.created_at.desc())
    )
    return [_serialize_bundle(item) for item in result.scalars().all()]


@router.post("/attestation-bundles/import")
async def import_attestation_bundle(
    request: BundleImportRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if str(request.bundle_payload.get("client_id")) != str(request.client_id):
        raise HTTPException(status_code=403, detail="Tenant isolation violation")
    bundle = BUNDLE_SERVICE.import_bundle(request.bundle_payload)
    bundle.client_id = request.client_id
    existing_result = await db.execute(
        select(AttestationFederationBundle).where(
            AttestationFederationBundle.client_id == request.client_id,
            AttestationFederationBundle.bundle_hash == bundle.bundle_hash,
        )
    )
    existing_bundle = existing_result.scalar_one_or_none()
    if existing_bundle:
        return {
            "bundle": _serialize_bundle(existing_bundle),
            "audit_event": build_attestation_audit_event(
                "attestation_bundle_imported",
                str(request.client_id),
                {"bundle_id": existing_bundle.id},
            ),
        }
    db.add(bundle)
    await db.commit()
    return {
        "bundle": _serialize_bundle(bundle),
        "audit_event": build_attestation_audit_event(
            "attestation_bundle_imported", str(request.client_id), {"bundle_id": bundle.id}
        ),
    }


@router.post("/attestation-bundles/{bundle_id}/verify")
async def verify_attestation_bundle(
    bundle_id: str,
    request: AttestationActionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    result = await db.execute(
        select(AttestationFederationBundle).where(
            AttestationFederationBundle.id == bundle_id,
            AttestationFederationBundle.client_id == request.client_id,
        )
    )
    bundle = result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    policy = await _get_or_create_policy(db, request.client_id)
    verification = BUNDLE_SERVICE.verify_bundle(bundle)
    policy_result = TRUST_ENGINE.evaluate_bundle(bundle, policy)
    await db.commit()
    return {"verification": verification, "policy_result": policy_result}


@router.get("/attestation-chains/{attestation_id}")
async def get_attestation_chain(
    attestation_id: str,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    attestation = await _get_attestation_or_404(db, attestation_id, client_id)
    result = await db.execute(
        select(SovereignExecutionAttestation)
        .where(
            SovereignExecutionAttestation.client_id == client_id,
            SovereignExecutionAttestation.subject_type == attestation.subject_type,
            SovereignExecutionAttestation.subject_ref == attestation.subject_ref,
        )
        .order_by(SovereignExecutionAttestation.created_at.asc())
    )
    chain = ATTESTATION_SERVICE.build_attestation_chain(result.scalars().all())
    chain_receipt = build_chain_receipt(chain)
    return {
        "chain": [
            {
                "attestation_id": item.attestation_id,
                "previous_link_hash": item.previous_link_hash,
                "current_link_hash": item.current_link_hash,
                "chain_position": item.chain_position,
                "replay_verifiable": item.replay_verifiable,
            }
            for item in chain
        ],
        "integrity_valid": ATTESTATION_SERVICE.validate_chain_integrity(chain),
        "chain_receipt": {
            **chain_receipt,
            "generated_at": chain_receipt["generated_at"].isoformat(),
        },
    }


@router.post("/attestations/{attestation_id}/receipt")
async def create_attestation_receipt(
    attestation_id: str,
    request: AttestationActionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    attestation = await _get_attestation_or_404(db, attestation_id, request.client_id)
    receipt_payload = build_attestation_receipt(attestation)
    existing_result = await db.execute(
        select(AttestationReceipt).where(
            AttestationReceipt.attestation_id == attestation.id,
            AttestationReceipt.immutable_hash == receipt_payload["immutable_hash"],
        )
    )
    existing_receipt = existing_result.scalar_one_or_none()
    if existing_receipt:
        return {
            "receipt": {
                **receipt_payload,
                "generated_at": existing_receipt.generated_at.isoformat(),
            },
            "audit_event": build_attestation_audit_event(
                "attestation_receipt_created",
                str(request.client_id),
                {"attestation_id": attestation.id},
            ),
        }
    receipt = AttestationReceipt(
        id=sha256_hex(
            {
                "kind": "attestation_receipt_id",
                "attestation_id": attestation.id,
                "immutable_hash": receipt_payload["immutable_hash"],
            }
        ),
        client_id=attestation.client_id,
        attestation_id=attestation.id,
        receipt_type=receipt_payload["receipt_type"],
        payload_hash=receipt_payload["payload_hash"],
        immutable_hash=receipt_payload["immutable_hash"],
        signature=receipt_payload["signature"],
    )
    db.add(receipt)
    await db.commit()
    return {
        "receipt": {
            **receipt_payload,
            "generated_at": receipt_payload["generated_at"].isoformat(),
        },
        "audit_event": build_attestation_audit_event(
            "attestation_receipt_created",
            str(request.client_id),
            {"attestation_id": attestation.id},
        ),
    }
