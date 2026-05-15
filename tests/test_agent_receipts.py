from app.services.agents.execution_receipts import build_action_receipt, verify_action_receipt


def test_action_receipt_build_and_verify():
    receipt = build_action_receipt(
        execution_id="exec-1",
        tenant_id="tenant-a",
        action_index=0,
        tool_name="echo",
        planned_input_hash="abc123",
        result_hash="def456",
        policy_decision="allowed",
        runtime_snapshot_hash="snap-1",
        previous_action_hash=None,
        execution_graph_hash="graph-1",
        sandbox_context={"mode": "internal", "shell_enabled": False},
    )
    assert receipt["receipt_hash"]
    assert verify_action_receipt(receipt) is True


def test_action_receipt_tamper_detection():
    receipt = build_action_receipt(
        execution_id="exec-1",
        tenant_id="tenant-a",
        action_index=1,
        tool_name="echo",
        planned_input_hash="abc123",
        result_hash="def456",
        policy_decision="allowed",
        runtime_snapshot_hash="snap-1",
        previous_action_hash="prev-1",
        execution_graph_hash="graph-1",
        sandbox_context={"mode": "internal", "shell_enabled": False},
    )
    receipt["body"]["result_hash"] = "tampered"
    assert verify_action_receipt(receipt) is False
