import uuid
from app.models.operations.adapter_promotion import (
    AdapterPromotionWorkflow,
    AdapterPromotionGateResult,
    AdapterPromotionStageTransition,
    AdapterPromotionRollback,
)
from app.services.operations.adapter_promotion.receipts import (
    build_promotion_workflow_receipt,
    build_gate_result_receipt,
    build_transition_receipt,
    build_rollback_receipt,
)

def test_build_receipts():
    client_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    
    workflow = AdapterPromotionWorkflow(
        id=workflow_id,
        client_id=client_id,
        adapter_name="test",
        adapter_version="1.0.0",
        target_stage="prod",
        input_hash="ihash",
        immutable_hash="wimm"
    )
    r1 = build_promotion_workflow_receipt(workflow)
    assert r1.receipt_type == "adapter_promotion_workflow"
    assert r1.signature_placeholder.startswith("promotion_sig_")

    gate = AdapterPromotionGateResult(
        id=uuid.uuid4(),
        client_id=client_id,
        workflow_id=workflow_id,
        gate_name="g1",
        gate_status="passed",
        immutable_hash="gimm"
    )
    r2 = build_gate_result_receipt(gate)
    assert r2.receipt_type == "adapter_promotion_gate"

    transition = AdapterPromotionStageTransition(
        id=uuid.uuid4(),
        client_id=client_id,
        workflow_id=workflow_id,
        from_stage="a",
        to_stage="b",
        transition_status="completed",
        immutable_hash="timm"
    )
    r3 = build_transition_receipt(transition)
    assert r3.receipt_type == "adapter_promotion_transition"

    rollback = AdapterPromotionRollback(
        id=uuid.uuid4(),
        client_id=client_id,
        workflow_id=workflow_id,
        from_stage="b",
        rollback_to_stage="a",
        reason="err",
        rollback_status="completed",
        immutable_hash="roimm"
    )
    r4 = build_rollback_receipt(rollback)
    assert r4.receipt_type == "adapter_promotion_rollback"
