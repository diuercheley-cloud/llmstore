# Owner: agent-platform
from __future__ import annotations

import uuid
from typing import Any

from app.models.commercial.commercial_workflows import (
    CommercialWorkflowApproval,
    CommercialWorkflowCheckpoint,
    CommercialWorkflowDefinition,
    CommercialWorkflowDeterminismReport,
    CommercialWorkflowExecution,
    CommercialWorkflowPolicySnapshot,
    CommercialWorkflowReceipt,
    CommercialWorkflowReplay,
    CommercialWorkflowReplaySession,
    CommercialWorkflowStage,
)
from app.services.auth import require_admin
from app.services.inference import workflow_determinism
from app.services.runtime_dependencies import get_db_session
from app.services.workflows.checkpoint_replay import WorkflowCheckpointReplayService
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.workflow_approval_chain import WorkflowApprovalChainService
from app.services.workflows.workflow_governance_ledger import WorkflowGovernanceLedgerService
from app.services.workflows.workflow_policy_enforcement import WorkflowPolicyEnforcementService
from app.services.workflows.workflow_provenance import WorkflowProvenanceService
from app.services.workflows.workflow_receipts import WorkflowReceiptService
from app.services.workflows.workflow_replay_sessions import WorkflowReplaySessionService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["admin", "workflows"], dependencies=[Depends(require_admin)])

_orchestrator = DeterministicWorkflowOrchestrator()
_receipts = WorkflowReceiptService()
_provenance = WorkflowProvenanceService()
_replay = WorkflowCheckpointReplayService()
_policy = WorkflowPolicyEnforcementService()
_approvals = WorkflowApprovalChainService()
_ledger = WorkflowGovernanceLedgerService()
_replay_sessions = WorkflowReplaySessionService()


class WorkflowDefinitionPayload(BaseModel):
    workflow_name: str = Field(min_length=1)
    steps_config: list[dict[str, Any]] | None = None
    dag_json: dict[str, Any] | None = None
    client_id: str | None = None
    workflow_family: str | None = None
    metadata_json: dict[str, Any] | None = None


class WorkflowExecutionPayload(BaseModel):
    definition_id: uuid.UUID
    session_id: str = Field(min_length=1)
    tenant_id: str | None = None
    request_id: str | None = None
    metadata_json: dict[str, Any] | None = None


class WorkflowStageCompletionPayload(BaseModel):
    input_data: Any
    output_data: Any
    state_snapshot: dict[str, Any] | None = None


class WorkflowRollbackPayload(BaseModel):
    checkpoint_id: uuid.UUID


class WorkflowPolicyRollbackPayload(BaseModel):
    actor_id: str = Field(min_length=1)


class WorkflowApprovalRequestPayload(BaseModel):
    requested_by: str = Field(min_length=1)
    approvers: list[str] = Field(min_length=1)
    delegated_approvers: list[str] | None = None
    ttl_seconds: int = Field(default=3600, ge=1)
    replay_safe: bool = True
    metadata_json: dict[str, Any] | None = None


class WorkflowApprovalDecisionPayload(BaseModel):
    execution_id: uuid.UUID
    stage_id: uuid.UUID
    approver: str = Field(min_length=1)
    status: str = Field(pattern="^(approved|rejected)$")
    notes: str | None = None
    emergency_override: bool = False
    actor_metadata_json: dict[str, Any] | None = None


class WorkflowReplaySessionPayload(BaseModel):
    original_execution_id: uuid.UUID
    replay_execution_id: uuid.UUID | None = None
    requested_by: str = Field(min_length=1)
    tenant_id: str | None = None
    metadata_json: dict[str, Any] | None = None


def _definition_summary(row: CommercialWorkflowDefinition) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "workflow_name": row.workflow_name,
        "workflow_family": row.workflow_family,
        "client_id": row.client_id,
        "version": row.version,
        "definition_hash": row.definition_hash,
        "entry_stage": row.entry_stage,
        "offline_compatible": row.offline_compatible,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _execution_summary(row: CommercialWorkflowExecution) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "definition_id": str(row.definition_id),
        "tenant_id": row.tenant_id,
        "status": row.status,
        "policy_gate_status": row.policy_gate_status,
        "determinism_status": row.determinism_status,
        "execution_hash_chain": row.execution_hash_chain,
        "ledger_hash": row.ledger_hash,
        "dag_hash": row.dag_hash,
        "current_step_index": row.current_step_index,
        "total_steps": row.total_steps,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _stage_summary(row: CommercialWorkflowStage) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "execution_id": str(row.execution_id),
        "stage_key": row.stage_key,
        "stage_name": row.stage_name,
        "stage_type": row.stage_type,
        "stage_order": row.stage_order,
        "status": row.status,
        "dependencies": row.dependencies_json or [],
        "policy_gate_status": row.policy_gate_status,
        "approval_required": row.approval_required,
        "approval_status": row.approval_status,
        "governance_mode": row.governance_mode,
        "drift_status": row.drift_status,
        "stage_hash": row.stage_hash,
        "checkpoint_hash": row.checkpoint_hash,
        "receipt_hash": row.receipt_hash,
    }


@router.get("/admin/inference/workflows/status")
@router.get("/admin/workflows/status")
async def get_status(db: AsyncSession = Depends(get_db_session)):
    return await workflow_determinism.summarize_workflow_determinism(db)


@router.get("/admin/inference/workflows/definitions")
@router.get("/admin/workflows/definitions")
async def list_definitions(db: AsyncSession = Depends(get_db_session)):
    rows = (
        (
            await db.execute(
                select(CommercialWorkflowDefinition)
                .order_by(desc(CommercialWorkflowDefinition.created_at))
                .limit(200)
            )
        )
        .scalars()
        .all()
    )
    return {"items": [_definition_summary(row) for row in rows]}


@router.post("/admin/inference/workflows/definitions")
@router.post("/admin/workflows/definitions")
async def create_definition(
    payload: WorkflowDefinitionPayload, db: AsyncSession = Depends(get_db_session)
):
    dag_or_steps = payload.dag_json or payload.steps_config or []
    row = await _orchestrator.create_definition(
        db,
        name=payload.workflow_name,
        dag_or_steps=dag_or_steps,
        client_id=payload.client_id,
        metadata_json=payload.metadata_json,
        workflow_family=payload.workflow_family,
    )
    await db.commit()
    await db.refresh(row)
    return _definition_summary(row)


@router.get("/admin/inference/workflows/executions")
@router.get("/admin/workflows/executions")
async def list_executions(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(CommercialWorkflowExecution)
        .order_by(desc(CommercialWorkflowExecution.started_at))
        .limit(200)
    )
    if tenant_id:
        stmt = stmt.where(CommercialWorkflowExecution.tenant_id == tenant_id)
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_execution_summary(row) for row in rows]}


@router.post("/admin/workflows/executions")
async def create_execution(
    payload: WorkflowExecutionPayload, db: AsyncSession = Depends(get_db_session)
):
    row = await _orchestrator.start_execution(
        db,
        definition_id=payload.definition_id,
        session_id=payload.session_id,
        tenant_id=payload.tenant_id,
        request_id=payload.request_id,
        metadata_json=payload.metadata_json,
    )
    await db.commit()
    await db.refresh(row)
    return _execution_summary(row)


@router.get("/admin/workflows/executions/{execution_id}")
async def get_execution(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    row = await db.get(CommercialWorkflowExecution, execution_id)
    if row is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    stages = (
        (
            await db.execute(
                select(CommercialWorkflowStage)
                .where(CommercialWorkflowStage.execution_id == execution_id)
                .order_by(CommercialWorkflowStage.stage_order.asc())
            )
        )
        .scalars()
        .all()
    )
    return {
        **_execution_summary(row),
        "stages": [_stage_summary(stage) for stage in stages],
    }


@router.post("/admin/workflows/executions/{execution_id}/stages/{stage_key}")
async def complete_stage(
    execution_id: uuid.UUID,
    stage_key: str,
    payload: WorkflowStageCompletionPayload,
    db: AsyncSession = Depends(get_db_session),
):
    row = await _orchestrator.complete_stage(
        db,
        execution_id=execution_id,
        stage_key=stage_key,
        input_data=payload.input_data,
        output_data=payload.output_data,
        state_snapshot=payload.state_snapshot,
    )
    await db.commit()
    await db.refresh(row)
    return _stage_summary(row)


@router.post("/admin/workflows/executions/{execution_id}/pause")
async def pause_execution(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    row = await _orchestrator.pause_execution(db, execution_id)
    await db.commit()
    await db.refresh(row)
    return _execution_summary(row)


@router.post("/admin/workflows/executions/{execution_id}/resume")
async def resume_execution(
    execution_id: uuid.UUID,
    resume_token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    row = await _orchestrator.resume_execution(db, execution_id, resume_token=resume_token)
    await db.commit()
    await db.refresh(row)
    return _execution_summary(row)


@router.post("/admin/workflows/executions/{execution_id}/rollback")
async def rollback_execution(
    execution_id: uuid.UUID,
    payload: WorkflowRollbackPayload,
    db: AsyncSession = Depends(get_db_session),
):
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    result = await _replay.rollback_to_checkpoint(
        db, execution=execution, checkpoint_id=payload.checkpoint_id
    )
    await db.commit()
    return result


@router.post(
    "/admin/workflows/governance/executions/{execution_id}/stages/{stage_key}/rollback-policy"
)
async def rollback_stage_policy(
    execution_id: uuid.UUID,
    stage_key: str,
    payload: WorkflowPolicyRollbackPayload,
    db: AsyncSession = Depends(get_db_session),
):
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    stage = (
        await db.execute(
            select(CommercialWorkflowStage).where(
                CommercialWorkflowStage.execution_id == execution_id,
                CommercialWorkflowStage.stage_key == stage_key,
            )
        )
    ).scalar_one_or_none()
    if stage is None:
        raise HTTPException(status_code=404, detail="workflow_stage_not_found")
    row = await _policy.rollback_stage_policy(
        db, execution=execution, stage=stage, actor_id=payload.actor_id
    )
    await db.commit()
    return {
        "binding_id": str(row.id),
        "rollback_from_binding_id": str(row.rollback_from_binding_id),
        "stage_key": stage_key,
    }


@router.get("/admin/workflows/executions/{execution_id}/provenance")
async def get_provenance(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    return await _provenance.build_execution_provenance(db, execution)


@router.get("/admin/workflows/governance/executions/{execution_id}")
async def get_governance_execution(
    execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
):
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    ledger_validation = await _ledger.validate_ledger(db, execution_id=execution.id)
    snapshots = await _policy.build_snapshot_view(db, execution_id=execution.id)
    events = await _ledger.list_events(db, execution_id=execution.id)
    return {
        **_execution_summary(execution),
        "ledger_validation": ledger_validation,
        "policy_snapshots": snapshots,
        "governance_events": [
            {
                "id": str(row.id),
                "event_type": row.event_type,
                "event_hash": row.event_hash,
                "ledger_hash": row.ledger_hash,
                "event_summary": row.event_summary,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in events
        ],
    }


@router.get("/admin/workflows/governance/executions/{execution_id}/ledger")
async def get_governance_ledger(
    execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
):
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    rows = await _ledger.list_events(db, execution_id=execution.id)
    return {
        "items": [
            {
                "id": str(row.id),
                "event_type": row.event_type,
                "stage_id": str(row.stage_id) if row.stage_id else None,
                "actor_id": row.actor_id,
                "event_summary": row.event_summary,
                "event_payload_json": row.event_payload_json or {},
                "previous_event_hash": row.previous_event_hash,
                "event_hash": row.event_hash,
                "ledger_hash": row.ledger_hash,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


@router.get("/admin/workflows/governance/executions/{execution_id}/snapshots")
async def get_policy_snapshots(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    return {"items": await _policy.build_snapshot_view(db, execution_id=execution.id)}


@router.get("/admin/workflows/executions/{execution_id}/checkpoints")
async def list_checkpoints(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    rows = (
        (
            await db.execute(
                select(CommercialWorkflowCheckpoint)
                .where(CommercialWorkflowCheckpoint.execution_id == execution_id)
                .order_by(
                    CommercialWorkflowCheckpoint.step_index.asc(),
                    CommercialWorkflowCheckpoint.created_at.asc(),
                )
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "stage_key": row.stage_key,
                "step_index": row.step_index,
                "snapshot_hash": row.snapshot_hash,
                "previous_checkpoint_hash": row.previous_checkpoint_hash,
                "detached_signature": row.detached_signature,
            }
            for row in rows
        ]
    }


@router.get("/admin/workflows/approvals")
async def list_workflow_approvals(
    execution_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(CommercialWorkflowApproval)
        .order_by(desc(CommercialWorkflowApproval.created_at))
        .limit(200)
    )
    if execution_id:
        stmt = stmt.where(CommercialWorkflowApproval.execution_id == execution_id)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "execution_id": str(row.execution_id),
                "stage_id": str(row.stage_id),
                "chain_id": row.chain_id,
                "event_type": row.event_type,
                "status": row.status,
                "step_index": row.step_index,
                "approver": row.approver,
                "requested_by": row.requested_by,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "decision_hash": row.decision_hash,
            }
            for row in rows
        ]
    }


@router.post("/admin/workflows/approvals/executions/{execution_id}/stages/{stage_key}/request")
async def request_stage_approval(
    execution_id: uuid.UUID,
    stage_key: str,
    payload: WorkflowApprovalRequestPayload,
    db: AsyncSession = Depends(get_db_session),
):
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    stage = (
        await db.execute(
            select(CommercialWorkflowStage).where(
                CommercialWorkflowStage.execution_id == execution_id,
                CommercialWorkflowStage.stage_key == stage_key,
            )
        )
    ).scalar_one_or_none()
    if stage is None:
        raise HTTPException(status_code=404, detail="workflow_stage_not_found")
    snapshot = (
        await db.get(CommercialWorkflowPolicySnapshot, stage.active_policy_snapshot_id)
        if stage.active_policy_snapshot_id
        else None
    )
    rows = await _approvals.request_approval(
        db,
        execution=execution,
        stage=stage,
        snapshot=snapshot,
        requested_by=payload.requested_by,
        approvers=payload.approvers,
        ttl_seconds=payload.ttl_seconds,
        delegated_approvers=payload.delegated_approvers,
        replay_safe=payload.replay_safe,
        metadata=payload.metadata_json,
    )
    await db.commit()
    return {"chain_id": rows[0].chain_id if rows else None, "items": len(rows)}


@router.post("/admin/workflows/approvals/{chain_id}/decide")
async def decide_stage_approval(
    chain_id: str,
    payload: WorkflowApprovalDecisionPayload,
    db: AsyncSession = Depends(get_db_session),
):
    execution = await db.get(CommercialWorkflowExecution, payload.execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="workflow_execution_not_found")
    stage = await db.get(CommercialWorkflowStage, payload.stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail="workflow_stage_not_found")
    try:
        row = await _approvals.record_decision(
            db,
            execution=execution,
            stage=stage,
            chain_id=chain_id,
            approver=payload.approver,
            status=payload.status,
            notes=payload.notes,
            emergency_override=payload.emergency_override,
            actor_metadata=payload.actor_metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return {"approval_id": str(row.id), "status": row.status, "event_type": row.event_type}


@router.get("/admin/workflows/replay-sessions")
async def list_replay_sessions(
    execution_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = (
        select(CommercialWorkflowReplaySession)
        .order_by(desc(CommercialWorkflowReplaySession.created_at))
        .limit(100)
    )
    if execution_id:
        stmt = stmt.where(CommercialWorkflowReplaySession.original_execution_id == execution_id)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "original_execution_id": str(row.original_execution_id),
                "replay_execution_id": str(row.replay_execution_id)
                if row.replay_execution_id
                else None,
                "tenant_id": row.tenant_id,
                "session_status": row.session_status,
                "policy_mismatch_detected": row.policy_mismatch_detected,
                "mismatch_detected": row.mismatch_detected,
                "report_hash": row.report_hash,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }
            for row in rows
        ]
    }


@router.post("/admin/workflows/replay-sessions")
async def create_replay_session(
    payload: WorkflowReplaySessionPayload, db: AsyncSession = Depends(get_db_session)
):
    try:
        row = await _orchestrator.create_replay_session(
            db,
            original_execution_id=payload.original_execution_id,
            replay_execution_id=payload.replay_execution_id,
            tenant_id=payload.tenant_id,
            requested_by=payload.requested_by,
            metadata_json=payload.metadata_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return {
        "id": str(row.id),
        "session_status": row.session_status,
        "deterministic_snapshot_hash": row.deterministic_snapshot_hash,
    }


@router.post("/admin/workflows/replay-sessions/{session_id}/complete")
async def complete_replay_session(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
):
    try:
        row = await _orchestrator.finalize_replay_session(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return {
        "id": str(row.id),
        "session_status": row.session_status,
        "mismatch_detected": row.mismatch_detected,
        "policy_mismatch_detected": row.policy_mismatch_detected,
        "report_hash": row.report_hash,
    }


@router.get("/admin/inference/workflows/replays")
@router.get("/admin/workflows/replays")
async def list_replays(db: AsyncSession = Depends(get_db_session)):
    rows = (
        (
            await db.execute(
                select(CommercialWorkflowReplay)
                .order_by(desc(CommercialWorkflowReplay.created_at))
                .limit(200)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "original_execution_id": str(row.original_execution_id),
                "replay_execution_id": str(row.replay_execution_id)
                if row.replay_execution_id
                else None,
                "status": row.status,
                "mismatched_step_index": row.mismatched_step_index,
                "replay_report": row.replay_report,
            }
            for row in rows
        ]
    }


@router.post("/admin/workflows/replay/{execution_id}")
async def create_replay(execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    row = await _orchestrator.initiate_replay(db, execution_id)
    await db.commit()
    await db.refresh(row)
    return {
        "id": str(row.id),
        "original_execution_id": str(row.original_execution_id),
        "status": row.status,
    }


@router.post("/admin/workflows/replay/{replay_id}/attach/{replay_execution_id}")
async def attach_replay_execution(
    replay_id: uuid.UUID,
    replay_execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    replay = await db.get(CommercialWorkflowReplay, replay_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="workflow_replay_not_found")
    replay.replay_execution_id = replay_execution_id
    await db.commit()
    await db.refresh(replay)
    return {"id": str(replay.id), "replay_execution_id": str(replay.replay_execution_id)}


@router.post("/admin/workflows/replay/{replay_id}/verify")
async def verify_replay(replay_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    row = await _orchestrator.verify_replay(db, replay_id)
    await db.commit()
    await db.refresh(row)
    return {
        "id": str(row.id),
        "execution_id": str(row.execution_id),
        "determinism_score": row.determinism_score,
        "drift_detected": row.drift_detected,
        "drift_summary": row.drift_summary,
    }


@router.get("/admin/inference/workflows/reports")
@router.get("/admin/workflows/reports")
async def list_reports(db: AsyncSession = Depends(get_db_session)):
    rows = (
        (
            await db.execute(
                select(CommercialWorkflowDeterminismReport)
                .order_by(desc(CommercialWorkflowDeterminismReport.created_at))
                .limit(200)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "execution_id": str(row.execution_id),
                "determinism_score": row.determinism_score,
                "drift_detected": row.drift_detected,
                "drift_summary": row.drift_summary,
            }
            for row in rows
        ]
    }


@router.get("/admin/workflows/receipts")
async def list_workflow_receipts(db: AsyncSession = Depends(get_db_session)):
    rows = (
        (
            await db.execute(
                select(CommercialWorkflowReceipt)
                .order_by(desc(CommercialWorkflowReceipt.created_at))
                .limit(200)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "execution_id": str(row.execution_id),
                "tenant_id": row.tenant_id,
                "receipt_hash": row.receipt_hash,
                "verification_status": row.verification_status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


@router.post("/admin/workflows/receipts/{execution_id}")
async def create_workflow_receipt(
    execution_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
):
    row = await _orchestrator.finalize_receipt(db, execution_id)
    await db.commit()
    await db.refresh(row)
    return await _receipts.export_receipt(row, include_sensitive=False)


@router.post("/admin/workflows/receipts/{receipt_id}/verify")
async def verify_workflow_receipt(
    receipt_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
):
    row = await db.get(CommercialWorkflowReceipt, receipt_id)
    if row is None:
        raise HTTPException(status_code=404, detail="workflow_receipt_not_found")
    result = await _receipts.verify_receipt(db, row)
    await db.commit()
    return result


@router.post("/admin/workflows/receipts/{receipt_id}/export")
async def export_workflow_receipt(
    receipt_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)
):
    row = await db.get(CommercialWorkflowReceipt, receipt_id)
    if row is None:
        raise HTTPException(status_code=404, detail="workflow_receipt_not_found")
    return await _receipts.export_receipt(row, include_sensitive=False)
