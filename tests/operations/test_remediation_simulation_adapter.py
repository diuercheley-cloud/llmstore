import pytest
from app.services.operations.remediation_execution.simulation_adapter import SimulatedRemediationExecutionAdapter

class TestSimulatedRemediationExecutionAdapter:
    def test_execute_step_deterministic(self):
        adapter = SimulatedRemediationExecutionAdapter()
        step = {"action_type": "restart", "target_domain": "worker", "target_ref": "node1"}
        res1 = adapter.execute_step(step)
        res2 = adapter.execute_step(step)
        assert res1["simulated_result_hash"] == res2["simulated_result_hash"]
        assert res1["status"] == "success"

    def test_execute_plan_all_steps(self):
        adapter = SimulatedRemediationExecutionAdapter()
        steps = [
            {"action_type": "a1", "target_domain": "d1", "target_ref": "r1"},
            {"action_type": "a2", "target_domain": "d2", "target_ref": "r2"}
        ]
        results = adapter.execute_plan({}, steps)
        assert len(results) == 2
        assert results[0]["action"] == "a1"
        assert results[1]["action"] == "a2"
