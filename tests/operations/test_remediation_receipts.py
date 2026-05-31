from app.services.operations.remediation.receipts import (
    build_remediation_plan_receipt,
    build_remediation_step_receipt,
    build_approval_requirement_receipt,
)

class TestRemediationReceipts:
    def test_build_plan_receipt(self):
        plan = {"id": "p1", "client_id": "c1", "deterministic_version": "v1", "dry_run": True}
        steps = [{"step_order": 1, "action_type": "test"}]
        receipt = build_remediation_plan_receipt(plan, steps)
        assert receipt["receipt_type"] == "remediation_plan_proposal"
        assert "immutable_hash" in receipt
        assert receipt["signature"] == "SIG_REMEDIATION_PLAN_PROPOSAL_V1"

    def test_build_step_receipt(self):
        step = {"id": "s1", "client_id": "c1", "action_type": "test", "dry_run": True}
        receipt = build_remediation_step_receipt(step)
        assert receipt["receipt_type"] == "remediation_step_proposal"
        assert "immutable_hash" in receipt

    def test_build_approval_receipt(self):
        req = {"id": "r1", "client_id": "c1", "approval_scope": "test"}
        receipt = build_approval_requirement_receipt(req)
        assert receipt["receipt_type"] == "remediation_approval_requirement"
        assert "immutable_hash" in receipt
