from app.services.operations.remediation_execution.receipts import (
    build_pre_execution_receipt,
    build_post_execution_receipt,
    build_kill_switch_receipt,
)

class TestRemediationExecutionReceipts:
    def test_build_pre_receipt(self):
        exec_data = {"id": "e1", "client_id": "c1", "deterministic_version": "v1", "dry_run": True}
        receipt = build_pre_execution_receipt(exec_data)
        assert receipt["receipt_type"] == "remediation_pre_execution"
        assert "immutable_hash" in receipt

    def test_build_post_receipt(self):
        exec_data = {"id": "e1", "client_id": "c1", "deterministic_version": "v1", "dry_run": True}
        results = [{"action": "a", "status": "success"}]
        receipt = build_post_execution_receipt(exec_data, results)
        assert receipt["receipt_type"] == "remediation_post_execution"
        assert "immutable_hash" in receipt

    def test_build_ks_receipt(self):
        ks_data = {"id": "k1", "client_id": "c1", "enabled": True}
        receipt = build_kill_switch_receipt(ks_data)
        assert receipt["receipt_type"] == "remediation_kill_switch_update"
