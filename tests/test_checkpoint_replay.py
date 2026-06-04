import pytest
from app.models.commercial_workflows import CommercialWorkflowCheckpoint
from app.services.workflows.checkpoint_replay import WorkflowCheckpointReplayService
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from sqlalchemy import select


@pytest.mark.asyncio
async def test_checkpoint_chain_and_rollback(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    replay = WorkflowCheckpointReplayService()
    definition = await orchestrator.create_definition(
        session,
        name="checkpoint-flow",
        dag_or_steps=[
            {"stage_key": "stage-1", "config": {"seed": 1}},
            {"stage_key": "stage-2", "dependencies": ["stage-1"], "config": {"seed": 2}},
        ],
        client_id="tenant-c",
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="sess-c",
        tenant_id="tenant-c",
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="stage-1",
        input_data={"x": 1},
        output_data={"y": 1},
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="stage-2",
        input_data={"y": 1},
        output_data={"z": 1},
    )
    await session.commit()

    checkpoints = (
        await session.execute(
            select(CommercialWorkflowCheckpoint)
            .where(CommercialWorkflowCheckpoint.execution_id == execution.id)
            .order_by(CommercialWorkflowCheckpoint.step_index.asc())
        )
    ).scalars().all()
    validation = await replay.validate_checkpoint_chain(session, execution.id)
    rollback = await replay.rollback_to_checkpoint(session, execution=execution, checkpoint_id=checkpoints[0].id)
    await session.commit()

    assert validation["valid"] is True
    assert len(checkpoints) == 2
    assert checkpoints[1].previous_checkpoint_hash == checkpoints[0].snapshot_hash
    assert "stage-2" in rollback["rolled_back_stages"]
    assert execution.status == "paused"
