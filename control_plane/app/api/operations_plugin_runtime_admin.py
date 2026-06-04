# Owner: platform-ops
# Classification: admin
import json
from typing import Any
from uuid import UUID

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.plugin_runtime import (
    PLUGIN_CONTRACT_SCOPES,
    PLUGIN_CONTRACT_STATUSES,
    DeterministicExtensionLoadPlan,
    PluginABIContract,
    PluginCapabilityBoundary,
    PluginFederationCompatibility,
    PluginIsolationPolicy,
    PluginLifecycleEvent,
    PluginReplayVerificationResult,
    PluginRuntimeActivation,
    PluginRuntimeCompatibilityCheck,
    PluginRuntimeExecution,
    PluginRuntimeReceipt,
)
from app.services.operations.plugin_runtime.abi_contracts import PluginABIContractService
from app.services.operations.plugin_runtime.audit_events import build_plugin_runtime_audit_event
from app.services.operations.plugin_runtime.capability_boundaries import (
    PluginCapabilityBoundaryService,
)
from app.services.operations.plugin_runtime.compatibility_enforcer import (
    PluginRuntimeCompatibilityEnforcer,
)
from app.services.operations.plugin_runtime.execution_runtime import (
    GovernedPluginRuntime,
    PluginExecutionError,
)
from app.services.operations.plugin_runtime.extension_loader import DeterministicExtensionLoader
from app.services.operations.plugin_runtime.federation_compatibility import (
    PluginFederationCompatibilityService,
)
from app.services.operations.plugin_runtime.hash_utils import compute_replay_hash, sha256_hex
from app.services.operations.plugin_runtime.isolation_policy import PluginIsolationPolicyService
from app.services.operations.plugin_runtime.lifecycle import PluginLifecycleService
from app.services.operations.plugin_runtime.receipts import (
    build_abi_contract_receipt,
    build_compatibility_receipt,
    build_federation_compatibility_receipt,
    build_load_plan_receipt,
    build_replay_verification_receipt,
)
from app.services.operations.plugin_runtime.replay_verifier import PluginReplayVerifier
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

CONTRACT_SERVICE = PluginABIContractService()
BOUNDARY_SERVICE = PluginCapabilityBoundaryService()
COMPATIBILITY_SERVICE = PluginRuntimeCompatibilityEnforcer()
LOADER = DeterministicExtensionLoader()
ISOLATION_SERVICE = PluginIsolationPolicyService()
LIFECYCLE_SERVICE = PluginLifecycleService()
REPLAY_VERIFIER = PluginReplayVerifier()
FEDERATION_SERVICE = PluginFederationCompatibilityService()
EXECUTION_RUNTIME = GovernedPluginRuntime


class ContractCreateRequest(BaseModel):
    client_id: UUID
    plugin_name: str
    plugin_version: str
    abi_version: str
    schema_version: str
    contract_scope: str
    contract_status: str = "draft"
    deterministic_version: str = "v1"


class CapabilityBoundaryRequest(BaseModel):
    client_id: UUID
    allowed_capabilities_json: list[str] = Field(default_factory=list)
    denied_capabilities_json: list[str] = Field(default_factory=list)
    isolation_required: bool = True
    offline_only: bool = True
    network_allowed: bool = False
    subprocess_allowed: bool = False
    filesystem_write_allowed: bool = False
    external_secret_access_allowed: bool = False


class CompatibilityCheckRequest(BaseModel):
    client_id: UUID
    runtime_version: str


class LoadPlanCreateRequest(BaseModel):
    client_id: UUID
    contract_ids: list[str]


class LifecycleRequest(BaseModel):
    client_id: UUID
    lifecycle_event_type: str
    reason: str = ""


class ReplayRequest(BaseModel):
    client_id: UUID


class FederationRequest(BaseModel):
    client_id: UUID
    source_environment: str
    target_environment: str


class ReceiptRequest(BaseModel):
    client_id: UUID
    receipt_type: str = "abi_contract_receipt"


class PluginActivationRequest(BaseModel):
    client_id: UUID
    load_plan_id: str | None = None


class PluginExecutionRequest(BaseModel):
    client_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    activation_id: str | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)


def _serialize_contract(item: PluginABIContract) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "plugin_name": item.plugin_name,
        "plugin_version": item.plugin_version,
        "abi_version": item.abi_version,
        "schema_version": item.schema_version,
        "contract_scope": item.contract_scope,
        "contract_status": item.contract_status,
        "deterministic_version": item.deterministic_version,
        "contract_hash": item.contract_hash,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_boundary(item: PluginCapabilityBoundary) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "allowed_capabilities_json": item.allowed_capabilities_json,
        "denied_capabilities_json": item.denied_capabilities_json,
        "isolation_required": item.isolation_required,
        "offline_only": item.offline_only,
        "network_allowed": item.network_allowed,
        "subprocess_allowed": item.subprocess_allowed,
        "filesystem_write_allowed": item.filesystem_write_allowed,
        "external_secret_access_allowed": item.external_secret_access_allowed,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_compatibility(item: PluginRuntimeCompatibilityCheck) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "runtime_version": item.runtime_version,
        "compatibility_status": item.compatibility_status,
        "replay_safe": item.replay_safe,
        "federation_safe": item.federation_safe,
        "reason": item.reason,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_load_plan(item: DeterministicExtensionLoadPlan) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "load_order": json.loads(item.load_order),
        "load_plan_hash": item.load_plan_hash,
        "load_status": item.load_status,
        "dry_run": item.dry_run,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_lifecycle(item: PluginLifecycleEvent) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "lifecycle_event_type": item.lifecycle_event_type,
        "lifecycle_status": item.lifecycle_status,
        "reason": item.reason,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_replay(item: PluginReplayVerificationResult) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "verification_status": item.verification_status,
        "replay_hash": item.replay_hash,
        "replay_safe": item.replay_safe,
        "deterministic_summary": item.deterministic_summary,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_federation(item: PluginFederationCompatibility) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "source_environment": item.source_environment,
        "target_environment": item.target_environment,
        "federation_status": item.federation_status,
        "compatibility_hash": item.compatibility_hash,
        "replay_safe": item.replay_safe,
        "immutable_hash": item.immutable_hash,
    }


def _serialize_receipt(item: PluginRuntimeReceipt) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "receipt_type": item.receipt_type,
        "payload_hash": item.payload_hash,
        "immutable_hash": item.immutable_hash,
        "signature": item.signature,
    }


def _serialize_activation(item: PluginRuntimeActivation) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "load_plan_id": item.load_plan_id,
        "activation_status": item.activation_status,
        "runtime_mode": item.runtime_mode,
        "artifact_locator": json.loads(item.artifact_locator),
        "immutable_hash": item.immutable_hash,
    }


def _serialize_execution(item: PluginRuntimeExecution) -> dict[str, Any]:
    return {
        "id": item.id,
        "client_id": str(item.client_id),
        "abi_contract_id": item.abi_contract_id,
        "activation_id": item.activation_id,
        "execution_status": item.execution_status,
        "runtime_mode": item.runtime_mode,
        "input_payload": item.input_payload,
        "output_payload": item.output_payload,
        "output_hash": item.output_hash,
        "error_message": item.error_message,
        "immutable_hash": item.immutable_hash,
    }


async def _get_contract(db: AsyncSession, contract_id: str, client_id: UUID) -> PluginABIContract:
    item = (
        await db.execute(
            select(PluginABIContract).where(
                PluginABIContract.id == contract_id,
                PluginABIContract.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Plugin ABI contract not found")
    return item


async def _get_load_plan(db: AsyncSession, load_plan_id: str, client_id: UUID) -> DeterministicExtensionLoadPlan:
    item = (
        await db.execute(
            select(DeterministicExtensionLoadPlan).where(
                DeterministicExtensionLoadPlan.id == load_plan_id,
                DeterministicExtensionLoadPlan.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Load plan not found")
    return item


async def _get_activation(db: AsyncSession, activation_id: str, client_id: UUID) -> PluginRuntimeActivation:
    item = (
        await db.execute(
            select(PluginRuntimeActivation).where(
                PluginRuntimeActivation.id == activation_id,
                PluginRuntimeActivation.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Plugin activation not found")
    return item


@router.post("/admin/operations/plugin-runtime/contracts")
async def create_contract(
    request: ContractCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    if request.contract_scope not in PLUGIN_CONTRACT_SCOPES:
        raise HTTPException(status_code=400, detail="Unsupported contract scope")
    if request.contract_status not in PLUGIN_CONTRACT_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported contract status")
    contract = CONTRACT_SERVICE.create_contract(request.model_dump())
    db.add(contract)
    policy = ISOLATION_SERVICE.create_default_policy(request.client_id)
    db.add(policy)
    await db.commit()
    return {
        "contract": _serialize_contract(contract),
        "isolation_policy": {
            "policy_name": policy.policy_name,
            "isolation_level": policy.isolation_level,
        },
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_abi_contract_created",
            str(contract.client_id),
            {"contract_id": contract.id, "plugin_name": contract.plugin_name},
        ),
    }


@router.get("/admin/operations/plugin-runtime/contracts")
async def list_contracts(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    rows = (
        await db.execute(
            select(PluginABIContract)
            .where(PluginABIContract.client_id == client_id)
            .order_by(PluginABIContract.plugin_name.asc(), PluginABIContract.plugin_version.asc())
        )
    ).scalars().all()
    return [_serialize_contract(item) for item in rows]


@router.get("/admin/operations/plugin-runtime/contracts/{contract_id}")
async def get_contract(
    contract_id: str,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, client_id)
    return {"contract": _serialize_contract(contract), "explanation": CONTRACT_SERVICE.explain_contract(contract)}


@router.post("/admin/operations/plugin-runtime/contracts/{contract_id}/capabilities")
async def evaluate_capabilities(
    contract_id: str,
    request: CapabilityBoundaryRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    boundary = BOUNDARY_SERVICE.build_boundary({**request.model_dump(), "abi_contract_id": contract.id})
    db.add(boundary)
    await db.commit()
    return {
        "boundary": _serialize_boundary(boundary),
        "evaluation": BOUNDARY_SERVICE.evaluate_capabilities(boundary),
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_capability_boundary_evaluated",
            str(contract.client_id),
            {"contract_id": contract.id, "boundary_id": boundary.id},
        ),
    }


@router.post("/admin/operations/plugin-runtime/contracts/{contract_id}/compatibility-check")
async def compatibility_check(
    contract_id: str,
    request: CompatibilityCheckRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    result = COMPATIBILITY_SERVICE.enforce_compatibility(contract, request.runtime_version)
    db.add(result)
    await db.commit()
    return {
        "compatibility": _serialize_compatibility(result),
        "explanation": COMPATIBILITY_SERVICE.explain_compatibility(result),
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_runtime_compatibility_checked",
            str(contract.client_id),
            {"contract_id": contract.id, "compatibility_id": result.id},
        ),
    }


@router.post("/admin/operations/plugin-runtime/load-plans")
async def create_load_plan(
    request: LoadPlanCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contracts = (
        await db.execute(
            select(PluginABIContract)
            .where(
                PluginABIContract.client_id == request.client_id,
                PluginABIContract.id.in_(request.contract_ids),
            )
            .order_by(PluginABIContract.plugin_name.asc(), PluginABIContract.plugin_version.asc())
        )
    ).scalars().all()
    if len(contracts) != len(request.contract_ids):
        raise HTTPException(status_code=404, detail="One or more contracts not found")
    plans = LOADER.build_load_plan(contracts)
    for plan in plans:
        last_check = (
            await db.execute(
                select(PluginRuntimeCompatibilityCheck)
                .where(
                    PluginRuntimeCompatibilityCheck.client_id == request.client_id,
                    PluginRuntimeCompatibilityCheck.abi_contract_id == plan.abi_contract_id,
                )
                .order_by(PluginRuntimeCompatibilityCheck.created_at.desc())
            )
        ).scalars().first()
        if last_check and last_check.compatibility_status in {"incompatible", "blocked"}:
            plan.load_status = "blocked"
        db.add(plan)
    await db.commit()
    return {
        "load_plans": [_serialize_load_plan(item) for item in plans],
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_load_plan_created",
            str(request.client_id),
            {"contract_count": len(plans), "dry_run": True},
        ),
    }


@router.post("/admin/operations/plugin-runtime/load-plans/{load_plan_id}/simulate")
async def simulate_load(
    load_plan_id: str,
    request: ReplayRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    load_plan = await _get_load_plan(db, load_plan_id, request.client_id)
    simulation = LOADER.simulate_load(load_plan)
    await db.commit()
    return {
        "load_plan": _serialize_load_plan(load_plan),
        "simulation": simulation,
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_load_simulated",
            str(request.client_id),
            {"load_plan_id": load_plan.id, "dry_run": True},
        ),
    }


@router.post("/admin/operations/plugin-runtime/contracts/{contract_id}/activate")
async def activate_plugin_runtime(
    contract_id: str,
    request: PluginActivationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    load_plan = None
    if request.load_plan_id:
        load_plan = await _get_load_plan(db, request.load_plan_id, request.client_id)
        if load_plan.abi_contract_id != contract.id:
            raise HTTPException(status_code=400, detail="Load plan does not belong to requested contract")
    runtime = EXECUTION_RUNTIME(db)
    try:
        activation = await runtime.activate(contract, load_plan)
    except PluginExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return {
        "activation": _serialize_activation(activation),
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_runtime_activated",
            str(contract.client_id),
            {"contract_id": contract.id, "activation_id": activation.id},
        ),
    }


@router.post("/admin/operations/plugin-runtime/contracts/{contract_id}/execute")
async def execute_plugin_runtime(
    contract_id: str,
    request: PluginExecutionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    runtime = EXECUTION_RUNTIME(db)
    activation = None
    if request.activation_id:
        activation = await _get_activation(db, request.activation_id, request.client_id)
        if activation.abi_contract_id != contract.id:
            raise HTTPException(status_code=400, detail="Activation does not belong to requested contract")
    else:
        try:
            activation = await runtime.activate(contract)
        except PluginExecutionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        execution = await runtime.execute(
            contract,
            request.payload,
            activation=activation,
            timeout_seconds=request.timeout_seconds,
        )
    except PluginExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return {
        "activation": _serialize_activation(activation),
        "execution": _serialize_execution(execution),
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_runtime_executed",
            str(contract.client_id),
            {"contract_id": contract.id, "activation_id": activation.id, "execution_id": execution.id},
        ),
    }


@router.post("/admin/operations/plugin-runtime/contracts/{contract_id}/lifecycle")
async def record_lifecycle(
    contract_id: str,
    request: LifecycleRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    lifecycle_map = {
        "submitted": lambda: LIFECYCLE_SERVICE.submit_plugin(contract),
        "reviewed": lambda: LIFECYCLE_SERVICE.mark_reviewed(contract),
        "compatibility_checked": lambda: LIFECYCLE_SERVICE.mark_compatibility_checked(contract),
        "sandbox_validated": lambda: LIFECYCLE_SERVICE.mark_sandbox_validated(contract),
        "placeholder_certified": lambda: LIFECYCLE_SERVICE.mark_placeholder_certified(contract),
        "deprecated": lambda: LIFECYCLE_SERVICE.deprecate_plugin(contract, request.reason),
        "revoked": lambda: LIFECYCLE_SERVICE.revoke_plugin(contract, request.reason),
        "blocked": lambda: LIFECYCLE_SERVICE.block_plugin(contract, request.reason),
        "activated": lambda: PluginLifecycleEvent(
            id=sha256_hex({"kind": "plugin_lifecycle_event_id", "client_id": str(contract.client_id), "abi_contract_id": contract.id, "lifecycle_event_type": "activated"}),
            client_id=contract.client_id,
            abi_contract_id=contract.id,
            lifecycle_event_type="activated",
            lifecycle_status="warning",
            reason="activation recorded without real plugin execution",
            immutable_hash=sha256_hex({"kind": "plugin_lifecycle_event", "client_id": str(contract.client_id), "abi_contract_id": contract.id, "lifecycle_event_type": "activated"}),
        ),
    }
    if request.lifecycle_event_type not in lifecycle_map:
        raise HTTPException(status_code=400, detail="Unsupported lifecycle event")
    event = lifecycle_map[request.lifecycle_event_type]()
    db.add(event)
    await db.commit()
    return {
        "lifecycle_event": _serialize_lifecycle(event),
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_lifecycle_event_recorded",
            str(contract.client_id),
            {"contract_id": contract.id, "event_type": event.lifecycle_event_type},
        ),
    }


@router.post("/admin/operations/plugin-runtime/contracts/{contract_id}/replay-verify")
async def replay_verify(
    contract_id: str,
    request: ReplayRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    replay = REPLAY_VERIFIER.replay_contract(contract)
    replay_hash = compute_replay_hash({"contract_hash": contract.contract_hash, "replayed": replay["replayed"]})
    result = PluginReplayVerificationResult(
        id=sha256_hex({"kind": "plugin_replay_verification_result_id", "client_id": str(contract.client_id), "abi_contract_id": contract.id, "replay_hash": replay_hash}),
        client_id=contract.client_id,
        abi_contract_id=contract.id,
        verification_status="passed" if replay["match"] else "failed",
        replay_hash=replay_hash,
        replay_safe=replay["match"],
        deterministic_summary=f"contract replay match={replay['match']}",
        immutable_hash=sha256_hex({"kind": "plugin_replay_verification_result", "client_id": str(contract.client_id), "abi_contract_id": contract.id, "replay_hash": replay_hash}),
    )
    db.add(result)
    await db.commit()
    return {
        "replay_verification": _serialize_replay(result),
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_replay_verified",
            str(contract.client_id),
            {"contract_id": contract.id, "verification_status": result.verification_status},
        ),
    }


@router.post("/admin/operations/plugin-runtime/contracts/{contract_id}/federation-compatibility")
async def federation_compatibility(
    contract_id: str,
    request: FederationRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    result = FEDERATION_SERVICE.evaluate_federation_compatibility(contract, request.source_environment, request.target_environment)
    db.add(result)
    await db.commit()
    return {
        "federation_compatibility": _serialize_federation(result),
        "summary": FEDERATION_SERVICE.build_federation_compatibility_summary(contract),
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_federation_compatibility_checked",
            str(contract.client_id),
            {"contract_id": contract.id, "federation_status": result.federation_status},
        ),
    }


@router.post("/admin/operations/plugin-runtime/contracts/{contract_id}/receipt")
async def generate_receipt(
    contract_id: str,
    request: ReceiptRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract = await _get_contract(db, contract_id, request.client_id)
    if request.receipt_type == "abi_contract_receipt":
        receipt_payload = build_abi_contract_receipt(contract)
    elif request.receipt_type == "compatibility_receipt":
        compatibility = (
            await db.execute(
                select(PluginRuntimeCompatibilityCheck)
                .where(
                    PluginRuntimeCompatibilityCheck.client_id == request.client_id,
                    PluginRuntimeCompatibilityCheck.abi_contract_id == contract.id,
                )
                .order_by(PluginRuntimeCompatibilityCheck.created_at.desc())
            )
        ).scalars().first()
        if compatibility is None:
            raise HTTPException(status_code=404, detail="Compatibility result not found")
        receipt_payload = build_compatibility_receipt(compatibility)
    elif request.receipt_type == "replay_verification_receipt":
        replay = (
            await db.execute(
                select(PluginReplayVerificationResult)
                .where(
                    PluginReplayVerificationResult.client_id == request.client_id,
                    PluginReplayVerificationResult.abi_contract_id == contract.id,
                )
                .order_by(PluginReplayVerificationResult.created_at.desc())
            )
        ).scalars().first()
        if replay is None:
            raise HTTPException(status_code=404, detail="Replay verification result not found")
        receipt_payload = build_replay_verification_receipt(replay)
    elif request.receipt_type == "federation_compatibility_receipt":
        federation = (
            await db.execute(
                select(PluginFederationCompatibility)
                .where(
                    PluginFederationCompatibility.client_id == request.client_id,
                    PluginFederationCompatibility.abi_contract_id == contract.id,
                )
                .order_by(PluginFederationCompatibility.created_at.desc())
            )
        ).scalars().first()
        if federation is None:
            raise HTTPException(status_code=404, detail="Federation compatibility result not found")
        receipt_payload = build_federation_compatibility_receipt(federation)
    elif request.receipt_type == "load_plan_receipt":
        load_plan = (
            await db.execute(
                select(DeterministicExtensionLoadPlan)
                .where(
                    DeterministicExtensionLoadPlan.client_id == request.client_id,
                    DeterministicExtensionLoadPlan.abi_contract_id == contract.id,
                )
                .order_by(DeterministicExtensionLoadPlan.created_at.desc())
            )
        ).scalars().first()
        if load_plan is None:
            raise HTTPException(status_code=404, detail="Load plan not found")
        receipt_payload = build_load_plan_receipt(load_plan)
    else:
        raise HTTPException(status_code=400, detail="Unsupported receipt type")
    receipt = PluginRuntimeReceipt(
        id=sha256_hex({"kind": "plugin_runtime_receipt_id", "client_id": str(contract.client_id), "abi_contract_id": contract.id, "receipt_type": receipt_payload["receipt_type"], "payload_hash": receipt_payload["payload_hash"]}),
        client_id=contract.client_id,
        abi_contract_id=contract.id,
        receipt_type=receipt_payload["receipt_type"],
        payload_hash=receipt_payload["payload_hash"],
        immutable_hash=receipt_payload["immutable_hash"],
        signature=receipt_payload["signature"],
        generated_at=receipt_payload["generated_at"],
    )
    db.add(receipt)
    await db.commit()
    return {
        "receipt": _serialize_receipt(receipt),
        "audit_event": build_plugin_runtime_audit_event(
            "plugin_runtime_receipt_created",
            str(contract.client_id),
            {"contract_id": contract.id, "receipt_type": receipt.receipt_type},
        ),
    }


@router.get("/admin/operations/plugin-runtime/summary")
async def plugin_runtime_summary(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin),
):
    contract_counts = (
        await db.execute(
            select(PluginABIContract.contract_status, func.count())
            .where(PluginABIContract.client_id == client_id)
            .group_by(PluginABIContract.contract_status)
        )
    ).all()
    async def _count(model: Any) -> int:
        return (await db.execute(select(func.count()).select_from(model).where(model.client_id == client_id))).scalar_one()
    compatibility_count = await _count(PluginRuntimeCompatibilityCheck)
    load_plan_count = await _count(DeterministicExtensionLoadPlan)
    activation_count = await _count(PluginRuntimeActivation)
    execution_count = await _count(PluginRuntimeExecution)
    replay_count = await _count(PluginReplayVerificationResult)
    federation_count = await _count(PluginFederationCompatibility)
    receipt_count = await _count(PluginRuntimeReceipt)
    lifecycle_count = await _count(PluginLifecycleEvent)
    policy = (
        await db.execute(
            select(PluginIsolationPolicy).where(PluginIsolationPolicy.client_id == client_id).order_by(PluginIsolationPolicy.created_at.desc())
        )
    ).scalars().first()
    return {
        "contract_statuses": {status: count for status, count in contract_counts},
        "compatibility_checks": compatibility_count,
        "load_plans": load_plan_count,
        "activations": activation_count,
        "executions": execution_count,
        "replay_verifications": replay_count,
        "federation_compatibility": federation_count,
        "receipts": receipt_count,
        "lifecycle_events": lifecycle_count,
        "isolation_policy_status": ISOLATION_SERVICE.validate_policy(policy) if policy else {"valid": False},
        "notice": {
            "no_real_plugin_execution": execution_count == 0,
            "sandboxed_plugin_execution_available": True,
            "placeholder_certification_only": True,
            "deterministic_load_simulation_only": execution_count == 0,
        },
    }
