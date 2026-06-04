import uuid

import pytest
from app.models.operations.adapter_promotion import (
    AdapterPromotionGateResult,
    AdapterPromotionReceipt,
    AdapterPromotionRollback,
    AdapterPromotionStageTransition,
    AdapterPromotionWorkflow,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_adapter_promotion_models_creation(session: AsyncSession):
    client_id = uuid.uuid4()
    registry_entry_id = uuid.uuid4()
    
    # Workflow
    workflow = AdapterPromotionWorkflow(
        client_id=client_id,
        registry_entry_id=registry_entry_id,
        adapter_name="test-adapter",
        adapter_version="1.0.0",
        target_stage="production_eligible",
        input_hash="ihash",
        immutable_hash="wf_imm_hash"
    )
    session.add(workflow)
    await session.flush()
    assert workflow.id is not None
    assert workflow.current_stage == "draft"

    # Gate Result
    gate = AdapterPromotionGateResult(
        client_id=client_id,
        workflow_id=workflow.id,
        gate_name="test_gate",
        gate_status="passed",
        immutable_hash="gate_imm_hash"
    )
    session.add(gate)
    await session.flush()
    assert gate.id is not None

    # Transition
    transition = AdapterPromotionStageTransition(
        client_id=client_id,
        workflow_id=workflow.id,
        from_stage="draft",
        to_stage="sandboxed",
        transition_status="completed",
        immutable_hash="trans_imm_hash"
    )
    session.add(transition)
    await session.flush()
    assert transition.id is not None

    # Receipt
    receipt = AdapterPromotionReceipt(
        client_id=client_id,
        workflow_id=workflow.id,
        receipt_type="test_receipt",
        payload_hash="phash",
        immutable_hash="rec_imm_hash",
        signature="sig"
    )
    session.add(receipt)
    await session.flush()
    assert receipt.id is not None

    # Rollback
    rollback = AdapterPromotionRollback(
        client_id=client_id,
        workflow_id=workflow.id,
        from_stage="sandboxed",
        rollback_to_stage="draft",
        reason="test rollback",
        rollback_status="completed",
        immutable_hash="roll_imm_hash"
    )
    session.add(rollback)
    await session.flush()
    assert rollback.id is not None
