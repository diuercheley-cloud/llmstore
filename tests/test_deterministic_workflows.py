import pytest
from sqlalchemy import select

from app.models.commercial_workflows import CommercialWorkflowReceipt, CommercialWorkflowStage
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator


@pytest.mark.asyncio
async def test_dag_execution_produces_deterministic_stage_chain(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    definition = await orchestrator.create_definition(
        session,
        name="phase55-dag",
        dag_or_steps={
            "stages": [
                {"stage_key": "summarize", "dependencies": [], "config": {"model": "local"}},
                {"stage_key": "classify", "dependencies": ["summarize"], "config": {"model": "local"}},
            ]
        },
        client_id="tenant-a",
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="sess-1",
        tenant_id="tenant-a",
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="summarize",
        input_data={"text": "hello"},
        output_data={"summary": "hello"},
        state_snapshot={"stage": 1},
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="classify",
        input_data={"summary": "hello"},
        output_data={"label": "ok"},
        state_snapshot={"stage": 2},
    )
    await session.commit()

    stages = (
        await session.execute(
            select(CommercialWorkflowStage)
            .where(CommercialWorkflowStage.execution_id == execution.id)
            .order_by(CommercialWorkflowStage.stage_order.asc())
        )
    ).scalars().all()
    receipt = (
        await session.execute(
            select(CommercialWorkflowReceipt).where(CommercialWorkflowReceipt.execution_id == execution.id)
        )
    ).scalar_one()

    assert execution.status == "completed"
    assert execution.execution_hash_chain is not None
    assert execution.ledger_hash is not None
    assert execution.provenance_hash is not None
    assert len(stages) == 2
    assert stages[0].stage_hash is not None
    assert stages[1].stage_hash is not None
    assert stages[1].lineage_hash is not None
    assert receipt.receipt_hash is not None
