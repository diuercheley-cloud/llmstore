import pytest
from app.models.commercial_workflows import CommercialWorkflowReceipt
from app.services.workflows.deterministic_orchestrator import DeterministicWorkflowOrchestrator
from app.services.workflows.workflow_receipts import WorkflowReceiptService
from sqlalchemy import select


@pytest.mark.asyncio
async def test_workflow_receipt_verification_detects_tampering(session):
    orchestrator = DeterministicWorkflowOrchestrator()
    receipts = WorkflowReceiptService()
    definition = await orchestrator.create_definition(
        session,
        name="receipt-flow",
        dag_or_steps=[{"stage_key": "stage-1", "config": {"seed": 1}}],
        client_id="tenant-r",
    )
    execution = await orchestrator.start_execution(
        session,
        definition_id=definition.id,
        session_id="sess-r",
        tenant_id="tenant-r",
    )
    await orchestrator.complete_stage(
        session,
        execution_id=execution.id,
        stage_key="stage-1",
        input_data={"x": 1},
        output_data={"y": 2},
    )
    await session.commit()

    receipt = (
        await session.execute(
            select(CommercialWorkflowReceipt).where(CommercialWorkflowReceipt.execution_id == execution.id)
        )
    ).scalar_one()
    first = await receipts.verify_receipt(session, receipt)
    assert first["verification_status"] == "verified"

    receipt.receipt_json["execution_hash_chain"] = "tampered"
    second = await receipts.verify_receipt(session, receipt)
    assert second["verification_status"] == "tampered"
