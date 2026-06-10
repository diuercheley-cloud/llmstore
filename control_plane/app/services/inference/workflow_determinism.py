from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from app.models.commercial.commercial_workflows import (
    CommercialWorkflowCheckpoint,
    CommercialWorkflowDefinition,
    CommercialWorkflowDeterminismReport,
    CommercialWorkflowExecution,
    CommercialWorkflowReplay,
    CommercialWorkflowStage,
)
from app.services.workflows.checkpoint_replay import WorkflowCheckpointReplayService
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_orchestrator = DeterministicWorkflowOrchestrator()
_checkpoints = WorkflowCheckpointReplayService()


async def create_workflow_definition(
    db: AsyncSession,
    name: str,
    steps_config: list[dict[str, Any]],
    client_id: str | None = None,
) -> CommercialWorkflowDefinition:
    definition = await _orchestrator.create_definition(
        db,
        name=name,
        dag_or_steps=steps_config,
        client_id=client_id,
    )
    await db.commit()
    await db.refresh(definition)
    return definition


async def start_workflow_execution(
    db: AsyncSession,
    definition_id: uuid.UUID,
    session_id: str,
    tenant_id: str | None = None,
) -> CommercialWorkflowExecution:
    execution = await _orchestrator.start_execution(
        db,
        definition_id=definition_id,
        session_id=session_id,
        tenant_id=tenant_id,
    )
    await db.commit()
    await db.refresh(execution)
    return execution


async def save_workflow_checkpoint(
    db: AsyncSession,
    execution_id: uuid.UUID,
    step_index: int,
    input_data: Any,
    output_data: Any,
    state: dict[str, Any] | None = None,
) -> CommercialWorkflowCheckpoint:
    execution = await db.get(CommercialWorkflowExecution, execution_id)
    if execution is None:
        raise ValueError("workflow_execution_not_found")
    stage = (
        await db.execute(
            select(CommercialWorkflowStage)
            .where(
                CommercialWorkflowStage.execution_id == execution_id,
                CommercialWorkflowStage.stage_order == step_index,
            )
        )
    ).scalar_one_or_none()
    if stage is not None:
        await _orchestrator.complete_stage(
            db,
            execution_id=execution_id,
            stage_key=stage.stage_key,
            input_data=input_data,
            output_data=output_data,
            state_snapshot=state,
        )
        await db.commit()
        checkpoint = (
            await db.execute(
                select(CommercialWorkflowCheckpoint)
                .where(
                    CommercialWorkflowCheckpoint.execution_id == execution_id,
                    CommercialWorkflowCheckpoint.stage_key == stage.stage_key,
                )
                .order_by(CommercialWorkflowCheckpoint.created_at.desc())
                .limit(1)
            )
        ).scalar_one()
        await db.refresh(checkpoint)
        return checkpoint
    checkpoint = await _checkpoints.create_checkpoint(
        db,
        execution=execution,
        stage=None,
        step_index=step_index,
        input_hash=None if input_data is None else hashlib.sha256(json.dumps(input_data, sort_keys=True, default=str).encode()).hexdigest(),
        output_hash=None if output_data is None else hashlib.sha256(json.dumps(output_data, sort_keys=True, default=str).encode()).hexdigest(),
        state_snapshot=state,
    )
    execution.current_step_index = max(execution.current_step_index, step_index + 1)
    if execution.current_step_index >= execution.total_steps:
        execution.status = "completed"
    await db.commit()
    await db.refresh(checkpoint)
    return checkpoint


async def initiate_workflow_replay(
    db: AsyncSession,
    original_execution_id: uuid.UUID,
) -> CommercialWorkflowReplay:
    replay = await _orchestrator.initiate_replay(db, original_execution_id)
    await db.commit()
    await db.refresh(replay)
    return replay


async def verify_determinism(
    db: AsyncSession,
    replay_id: uuid.UUID,
) -> CommercialWorkflowDeterminismReport:
    report = await _orchestrator.verify_replay(db, replay_id)
    await db.commit()
    await db.refresh(report)
    return report


async def summarize_workflow_determinism(db: AsyncSession) -> dict[str, Any]:
    return await _orchestrator.summarize(db)
