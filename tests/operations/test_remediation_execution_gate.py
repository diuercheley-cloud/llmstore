from app.services.operations.remediation_execution.execution_gate import RemediationExecutionGate


class TestRemediationExecutionGate:
    def test_verify_approval_needed_and_missing(self):
        gate = RemediationExecutionGate()
        plan = {"requires_approval": True}
        approvals = []
        assert gate.verify_approval(plan, approvals) is False

    def test_verify_approval_present(self):
        gate = RemediationExecutionGate()
        plan = {"requires_approval": True}
        approvals = [{"status": "approved"}]
        assert gate.verify_approval(plan, approvals) is True

    def test_kill_switch_blocks(self):
        gate = RemediationExecutionGate()
        ks = {"enabled": True}
        assert gate.verify_kill_switch(ks) is False # Safe check returns False if enabled

    def test_can_execute_dry_run_always_true_for_approval(self):
        gate = RemediationExecutionGate()
        plan = {"requires_approval": True, "blast_radius": "low"}
        res = gate.can_execute(plan, [], {"rollback_steps_json": [1]}, None, dry_run=True)
        assert res["can_execute"] is True
        assert res["approval_verified"] is True # True because dry_run
