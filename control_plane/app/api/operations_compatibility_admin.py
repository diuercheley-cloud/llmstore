# Owner: platform-ops
from typing import Any
from uuid import UUID

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.compatibility_contracts import (
    CAPABILITY_NEGOTIATION_STATUSES,
    COMPATIBILITY_STATUSES,
    COMPATIBILITY_TYPES,
    CONTRACT_SCOPES,
    CONTRACT_STATUSES,
    NEGOTIATION_STATUSES,
    VERIFICATION_STATUSES,
    CapabilityNegotiation,
    CompatibilityContract,
    CompatibilityMatrix,
    CompatibilityReceipt,
    CompatibilityVerificationResult,
    DeprecationLifecycle,
    VersionNegotiationSession,
)
from app.services.operations.compatibility_contracts.audit_events import (
    build_compatibility_audit_event,
)
from app.services.operations.compatibility_contracts.capability_negotiation import (
    CapabilityNegotiationService,
)
from app.services.operations.compatibility_contracts.compatibility_matrix import (
    CompatibilityMatrixService,
)
from app.services.operations.compatibility_contracts.deprecation_lifecycle import (
    DeprecationLifecycleService,
)
from app.services.operations.compatibility_contracts.hash_utils import (
    compute_contract_hash,
    compute_matrix_hash,
    compute_negotiation_hash,
    sha256_hex,
)
from app.services.operations.compatibility_contracts.receipts import (
    build_contract_receipt,
    build_deprecation_receipt,
    build_negotiation_receipt,
    build_verification_receipt,
)
from app.services.operations.compatibility_contracts.validation import validate_schema_compatibility
from app.services.operations.compatibility_contracts.verification import (
    CompatibilityVerificationService,
)
from app.services.operations.compatibility_contracts.version_negotiation import (
    VersionNegotiationService,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["operations-compatibility"])

MATRIX_SERVICE = CompatibilityMatrixService()
NEGOTIATION_SERVICE = VersionNegotiationService()
CAPABILITY_SERVICE = CapabilityNegotiationService()
DEPRECATION_SERVICE = DeprecationLifecycleService()
VERIFICATION_SERVICE = CompatibilityVerificationService()


class ContractCreateRequest(BaseModel):
    client_id: UUID
    contract_name: str
    contract_scope: str
    semantic_version: str
    schema_version: str
    compatibility_status: str = "active"
    deterministic_version: str = "v1"
    feature_flags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


class MatrixCreateRequest(BaseModel):
    client_id: UUID
    source_version: str
    target_version: str


class VersionNegotiationRequest(BaseModel):
    client_id: UUID
    source_environment: str
    target_environment: str
    source_version: str
    target_version: str
    source_contract_id: str | None = None
    target_contract_id: str | None = None


class CapabilityNegotiationRequest(BaseModel):
    client_id: UUID
    negotiation_session_id: str
    requested_capabilities: list[str]
    available_capabilities: list[str]


class VerificationRequest(BaseModel):
    client_id: UUID


class DeprecationRequest(BaseModel):
    client_id: UUID
    deprecation_reason: str
    migration_required: bool = False
    replacement_contract: str | None = None
    announce: bool = False
    enforce: bool = False


class ReceiptRequest(BaseModel):
    client_id: UUID
    receipt_type: str = "contract_receipt"


def _serialize_contract(item: CompatibilityContract) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "contract_name": item.contract_name,
        "contract_scope": item.contract_scope,
        "semantic_version": item.semantic_version,
        "schema_version": item.schema_version,
        "compatibility_status": item.compatibility_status,
        "deterministic_version": item.deterministic_version,
        "contract_hash": item.contract_hash,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_matrix(item: CompatibilityMatrix) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "source_version": item.source_version,
        "target_version": item.target_version,
        "compatibility_type": item.compatibility_type,
        "compatibility_status": item.compatibility_status,
        "upgrade_supported": item.upgrade_supported,
        "downgrade_supported": item.downgrade_supported,
        "replay_safe": item.replay_safe,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_session(item: VersionNegotiationSession) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "source_environment": item.source_environment,
        "target_environment": item.target_environment,
        "source_version": item.source_version,
        "target_version": item.target_version,
        "negotiated_version": item.negotiated_version,
        "negotiation_status": item.negotiation_status,
        "replay_verifiable": item.replay_verifiable,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_capabilities(item: CapabilityNegotiation) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "negotiation_session_id": item.negotiation_session_id,
        "requested_capabilities_json": item.requested_capabilities_json,
        "approved_capabilities_json": item.approved_capabilities_json,
        "denied_capabilities_json": item.denied_capabilities_json,
        "negotiation_status": item.negotiation_status,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_deprecation(item: DeprecationLifecycle) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "contract_id": item.contract_id,
        "deprecation_reason": item.deprecation_reason,
        "deprecation_status": item.deprecation_status,
        "replacement_contract": item.replacement_contract,
        "migration_required": item.migration_required,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_verification(item: CompatibilityVerificationResult) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "contract_id": item.contract_id,
        "verification_type": item.verification_type,
        "verification_status": item.verification_status,
        "replay_safe": item.replay_safe,
        "compatibility_summary": item.compatibility_summary,
        "immutable_hash": item.immutable_hash,
    }


async def _get_contract(
    db: AsyncSession, contract_id: str, client_id: UUID
) -> CompatibilityContract:
    contract = (
        await db.execute(
            select(CompatibilityContract).where(
                CompatibilityContract.id == contract_id,
                CompatibilityContract.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Compatibility contract not found")
    return contract


async def _get_session(
    db: AsyncSession, session_id: str, client_id: UUID
) -> VersionNegotiationSession:
    item = (
        await db.execute(
            select(VersionNegotiationSession).where(
                VersionNegotiationSession.id == session_id,
                VersionNegotiationSession.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Version negotiation session not found")
    return item


@router.post("/admin/operations/compatibility/contracts")
async def create_contract(
    request: ContractCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if request.contract_scope not in CONTRACT_SCOPES:
        raise HTTPException(status_code=400, detail="Unsupported contract scope")
    if request.compatibility_status not in CONTRACT_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported compatibility status")
    schema_validation = validate_schema_compatibility(
        request.schema_version, request.schema_version
    )
    contract_payload = {
        "client_id": str(request.client_id),
        "contract_name": request.contract_name,
        "contract_scope": request.contract_scope,
        "semantic_version": request.semantic_version,
        "schema_version": request.schema_version,
        "compatibility_status": request.compatibility_status,
        "deterministic_version": request.deterministic_version,
        "feature_flags": sorted(request.feature_flags),
        "capabilities": sorted(request.capabilities),
    }
    contract_hash = compute_contract_hash(contract_payload)
    contract = CompatibilityContract(
        id=sha256_hex({"kind": "compatibility_contract_id", **contract_payload}),
        client_id=request.client_id,
        contract_name=request.contract_name,
        contract_scope=request.contract_scope,
        semantic_version=request.semantic_version,
        schema_version=request.schema_version,
        compatibility_status=request.compatibility_status,
        deterministic_version=request.deterministic_version,
        contract_hash=contract_hash,
        immutable_hash=sha256_hex(
            {"kind": "compatibility_contract_immutable", "contract_hash": contract_hash}
        ),
    )
    db.add(contract)
    await db.commit()
    return {
        "contract": _serialize_contract(contract),
        "schema_validation": schema_validation,
        "audit_event": build_compatibility_audit_event(
            "compatibility_contract_created",
            str(contract.client_id),
            {"contract_id": contract.id, "contract_name": contract.contract_name},
        ),
    }


@router.get("/admin/operations/compatibility/contracts")
async def list_contracts(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        (
            await db.execute(
                select(CompatibilityContract)
                .where(CompatibilityContract.client_id == client_id)
                .order_by(CompatibilityContract.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [_serialize_contract(item) for item in rows]


@router.get("/admin/operations/compatibility/contracts/{contract_id}")
async def get_contract(
    contract_id: str,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, client_id)
    return _serialize_contract(contract)


@router.post("/admin/operations/compatibility/matrix")
async def create_matrix(
    request: MatrixCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    matrix_result = MATRIX_SERVICE.build_matrix(request.source_version, request.target_version)
    if matrix_result["compatibility_type"] not in COMPATIBILITY_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported compatibility type")
    if matrix_result["compatibility_status"] not in COMPATIBILITY_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported compatibility status")
    immutable_hash = compute_matrix_hash(
        {
            "client_id": str(request.client_id),
            "source_version": request.source_version,
            "target_version": request.target_version,
            "compatibility_type": matrix_result["compatibility_type"],
            "compatibility_status": matrix_result["compatibility_status"],
            "upgrade_supported": matrix_result["upgrade_supported"],
            "downgrade_supported": matrix_result["downgrade_supported"],
            "replay_safe": matrix_result["replay_safe"],
        }
    )
    matrix = CompatibilityMatrix(
        id=sha256_hex(
            {
                "kind": "compatibility_matrix_id",
                "client_id": str(request.client_id),
                "immutable_hash": immutable_hash,
            }
        ),
        client_id=request.client_id,
        source_version=request.source_version,
        target_version=request.target_version,
        compatibility_type=matrix_result["compatibility_type"],
        compatibility_status=matrix_result["compatibility_status"],
        upgrade_supported=matrix_result["upgrade_supported"],
        downgrade_supported=matrix_result["downgrade_supported"],
        replay_safe=matrix_result["replay_safe"],
        immutable_hash=immutable_hash,
    )
    db.add(matrix)
    await db.commit()
    return {
        "matrix": _serialize_matrix(matrix),
        "explanation": MATRIX_SERVICE.explain_matrix(matrix_result),
        "audit_event": build_compatibility_audit_event(
            "compatibility_matrix_created",
            str(matrix.client_id),
            {
                "matrix_id": matrix.id,
                "source_version": matrix.source_version,
                "target_version": matrix.target_version,
            },
        ),
    }


@router.post("/admin/operations/compatibility/negotiate")
async def negotiate_versions(
    request: VersionNegotiationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    source_contract = None
    target_contract = None
    if request.source_contract_id:
        source_contract = await _get_contract(db, request.source_contract_id, request.client_id)
        if source_contract.compatibility_status == "blocked":
            raise HTTPException(
                status_code=409, detail="Blocked source contract cannot be negotiated"
            )
    if request.target_contract_id:
        target_contract = await _get_contract(db, request.target_contract_id, request.client_id)
        if target_contract.compatibility_status == "blocked":
            raise HTTPException(
                status_code=409, detail="Blocked target contract cannot be negotiated"
            )
    negotiation = NEGOTIATION_SERVICE.negotiate(request.source_version, request.target_version)
    if negotiation["negotiation_status"] not in NEGOTIATION_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported negotiation status")
    payload = {
        "client_id": str(request.client_id),
        "source_environment": request.source_environment,
        "target_environment": request.target_environment,
        "source_version": request.source_version,
        "target_version": request.target_version,
        "negotiated_version": negotiation["negotiated_version"],
        "negotiation_status": negotiation["negotiation_status"],
        "replay_verifiable": negotiation["replay_verifiable"],
    }
    session = VersionNegotiationSession(
        id=sha256_hex({"kind": "version_negotiation_session_id", **payload}),
        client_id=request.client_id,
        source_environment=request.source_environment,
        target_environment=request.target_environment,
        source_version=request.source_version,
        target_version=request.target_version,
        negotiated_version=negotiation["negotiated_version"],
        negotiation_status=negotiation["negotiation_status"],
        replay_verifiable=negotiation["replay_verifiable"],
        immutable_hash=compute_negotiation_hash(payload),
    )
    db.add(session)
    await db.commit()
    return {
        "session": _serialize_session(session),
        "matrix": negotiation["matrix"],
        "explanation": NEGOTIATION_SERVICE.explain_negotiation(session),
        "audit_events": [
            build_compatibility_audit_event(
                "version_negotiation_started",
                str(session.client_id),
                {
                    "session_id": session.id,
                    "source_environment": session.source_environment,
                    "target_environment": session.target_environment,
                },
            ),
            build_compatibility_audit_event(
                "version_negotiation_completed",
                str(session.client_id),
                {
                    "session_id": session.id,
                    "negotiated_version": session.negotiated_version,
                    "status": session.negotiation_status,
                },
            ),
        ],
    }


@router.post("/admin/operations/compatibility/capabilities/negotiate")
async def negotiate_capabilities(
    request: CapabilityNegotiationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    session = await _get_session(db, request.negotiation_session_id, request.client_id)
    result = CAPABILITY_SERVICE.negotiate_capabilities(
        request.requested_capabilities, request.available_capabilities
    )
    if result["negotiation_status"] not in CAPABILITY_NEGOTIATION_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported capability negotiation status")
    item = CapabilityNegotiation(
        id=sha256_hex(
            {
                "kind": "capability_negotiation_id",
                "client_id": str(request.client_id),
                "session_id": session.id,
                "approved": result["approved_capabilities"],
                "denied": result["denied_capabilities"],
            }
        ),
        client_id=request.client_id,
        negotiation_session_id=session.id,
        requested_capabilities_json=result["requested_capabilities"],
        approved_capabilities_json=result["approved_capabilities"],
        denied_capabilities_json=result["denied_capabilities"],
        negotiation_status=result["negotiation_status"],
        immutable_hash=sha256_hex(
            {"kind": "capability_negotiation_immutable", "session_id": session.id, **result}
        ),
    )
    db.add(item)
    await db.commit()
    return {
        "capability_negotiation": _serialize_capabilities(item),
        "verification": VERIFICATION_SERVICE.verify_capabilities(result),
        "audit_event": build_compatibility_audit_event(
            "capability_negotiation_completed",
            str(item.client_id),
            {
                "negotiation_session_id": item.negotiation_session_id,
                "status": item.negotiation_status,
            },
        ),
    }


@router.post("/admin/operations/compatibility/contracts/{contract_id}/verify")
async def verify_contract(
    contract_id: str,
    request: VerificationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    result = VERIFICATION_SERVICE.verify_contract(contract)
    if result["verification_status"] not in VERIFICATION_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported verification status")
    record = CompatibilityVerificationResult(
        id=sha256_hex(
            {"kind": "compatibility_verification_id", "contract_id": contract.id, **result}
        ),
        client_id=request.client_id,
        contract_id=contract.id,
        verification_type=result["verification_type"],
        verification_status=result["verification_status"],
        replay_safe=result["replay_safe"],
        compatibility_summary=result["compatibility_summary"],
        immutable_hash=sha256_hex(
            {"kind": "compatibility_verification_immutable", "contract_id": contract.id, **result}
        ),
    )
    db.add(record)
    await db.commit()
    return {
        "verification": _serialize_verification(record),
        "audit_event": build_compatibility_audit_event(
            "compatibility_verification_completed",
            str(record.client_id),
            {"contract_id": record.contract_id, "verification_status": record.verification_status},
        ),
    }


@router.post("/admin/operations/compatibility/contracts/{contract_id}/deprecate")
async def deprecate_contract(
    contract_id: str,
    request: DeprecationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    lifecycle = DeprecationLifecycle(
        id=sha256_hex(
            {
                "kind": "deprecation_lifecycle_id",
                "contract_id": contract.id,
                "deprecation_reason": request.deprecation_reason,
                "replacement_contract": request.replacement_contract,
                "migration_required": request.migration_required,
            }
        ),
        client_id=request.client_id,
        contract_id=contract.id,
        deprecation_reason=request.deprecation_reason,
        deprecation_status="proposed",
        replacement_contract=request.replacement_contract,
        migration_required=request.migration_required,
        immutable_hash=sha256_hex(
            {
                "kind": "deprecation_lifecycle_immutable",
                "contract_id": contract.id,
                "deprecation_reason": request.deprecation_reason,
                "replacement_contract": request.replacement_contract,
                "migration_required": request.migration_required,
            }
        ),
    )
    transition = DEPRECATION_SERVICE.propose_deprecation(lifecycle)
    contract.compatibility_status = "deprecated"
    events = [
        build_compatibility_audit_event(
            "deprecation_proposed",
            str(request.client_id),
            {"contract_id": contract.id, "deprecation_status": transition["deprecation_status"]},
        )
    ]
    if request.announce:
        transition = DEPRECATION_SERVICE.announce_deprecation(lifecycle)
        lifecycle.deprecation_status = transition["deprecation_status"]
        events.append(
            build_compatibility_audit_event(
                "deprecation_announced",
                str(request.client_id),
                {
                    "contract_id": contract.id,
                    "deprecation_status": transition["deprecation_status"],
                },
            )
        )
    if request.enforce:
        transition = DEPRECATION_SERVICE.enforce_deprecation(lifecycle)
        lifecycle.deprecation_status = transition["deprecation_status"]
        contract.compatibility_status = "blocked"
        events.append(
            build_compatibility_audit_event(
                "deprecation_enforced",
                str(request.client_id),
                {
                    "contract_id": contract.id,
                    "deprecation_status": transition["deprecation_status"],
                },
            )
        )
    db.add(lifecycle)
    await db.commit()
    return {
        "deprecation": _serialize_deprecation(lifecycle),
        "contract": _serialize_contract(contract),
        "audit_events": events,
    }


@router.get("/admin/operations/compatibility/deprecations")
async def list_deprecations(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        (
            await db.execute(
                select(DeprecationLifecycle)
                .where(DeprecationLifecycle.client_id == client_id)
                .order_by(DeprecationLifecycle.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [_serialize_deprecation(item) for item in rows]


@router.post("/admin/operations/compatibility/contracts/{contract_id}/receipt")
async def create_receipt(
    contract_id: str,
    request: ReceiptRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    receipt_payload = build_contract_receipt(contract)
    if request.receipt_type == "verification_receipt":
        verification = (
            (
                await db.execute(
                    select(CompatibilityVerificationResult)
                    .where(
                        CompatibilityVerificationResult.contract_id == contract.id,
                        CompatibilityVerificationResult.client_id == request.client_id,
                    )
                    .order_by(CompatibilityVerificationResult.created_at.desc())
                )
            )
            .scalars()
            .first()
        )
        if not verification:
            raise HTTPException(status_code=404, detail="No verification result available")
        receipt_payload = build_verification_receipt(verification)
    elif request.receipt_type == "deprecation_receipt":
        lifecycle = (
            (
                await db.execute(
                    select(DeprecationLifecycle)
                    .where(
                        DeprecationLifecycle.contract_id == contract.id,
                        DeprecationLifecycle.client_id == request.client_id,
                    )
                    .order_by(DeprecationLifecycle.created_at.desc())
                )
            )
            .scalars()
            .first()
        )
        if not lifecycle:
            raise HTTPException(status_code=404, detail="No deprecation lifecycle available")
        receipt_payload = build_deprecation_receipt(lifecycle)
    elif request.receipt_type == "negotiation_receipt":
        negotiation = (
            (
                await db.execute(
                    select(VersionNegotiationSession)
                    .where(VersionNegotiationSession.client_id == request.client_id)
                    .order_by(VersionNegotiationSession.created_at.desc())
                )
            )
            .scalars()
            .first()
        )
        if not negotiation:
            raise HTTPException(status_code=404, detail="No version negotiation available")
        receipt_payload = build_negotiation_receipt(negotiation)
    receipt = CompatibilityReceipt(
        id=sha256_hex(
            {
                "kind": "compatibility_receipt_id",
                "contract_id": contract.id,
                "receipt_type": receipt_payload["receipt_type"],
                "payload_hash": receipt_payload["payload_hash"],
            }
        ),
        client_id=request.client_id,
        contract_id=contract.id,
        receipt_type=receipt_payload["receipt_type"],
        payload_hash=receipt_payload["payload_hash"],
        immutable_hash=receipt_payload["immutable_hash"],
        signature=receipt_payload["signature"],
        generated_at=receipt_payload["generated_at"],
    )
    db.add(receipt)
    await db.commit()
    return {
        "receipt": {
            **receipt_payload,
            "id": receipt.id,
            "contract_id": receipt.contract_id,
        },
        "audit_event": build_compatibility_audit_event(
            "compatibility_receipt_created",
            str(request.client_id),
            {"contract_id": contract.id, "receipt_type": receipt.receipt_type},
        ),
    }
