from app.services.operations.remediation.deterministic_planner import (
    DeterministicRemediationPlanner,
)


class TestDeterministicRemediationPlanner:
    def test_normalize_inputs(self):
        planner = DeterministicRemediationPlanner()
        inputs = {"b": 2, "a": 1}
        normalized = planner.normalize_inputs(inputs)
        assert list(normalized.keys()) == ["a", "b"]

    def test_compute_input_hash_is_deterministic(self):
        planner = DeterministicRemediationPlanner()
        inputs = {"source_type": "forecast", "source_ref": "f1"}
        h1 = planner.compute_input_hash(inputs)
        h2 = planner.compute_input_hash(inputs)
        assert h1 == h2

    def test_build_plan_risk_logic(self):
        planner = DeterministicRemediationPlanner()
        inputs = {"source_type": "forecast", "risk_level": "critical", "involved_domains": ["auth"]}
        plan = planner.build_plan(inputs)
        assert plan["risk_level"] == "critical"
        assert plan["requires_approval"] is True
        assert plan["blast_radius"] == "high" # Due to critical risk

    def test_build_steps_structure(self):
        planner = DeterministicRemediationPlanner()
        inputs = {"involved_domains": ["auth", "billing"]}
        plan = planner.build_plan(inputs)
        steps = planner.build_steps(plan, inputs)
        
        # Containment (2) + Mitigation (2) + Validation (1) = 5
        assert len(steps) == 5
        assert steps[0]["action_type"] == "containment"
        assert steps[-1]["action_type"] == "validation"

    def test_explain_plan(self):
        planner = DeterministicRemediationPlanner()
        inputs = {"source_type": "forecast", "risk_level": "low", "involved_domains": ["auth"]}
        plan = planner.build_plan(inputs)
        steps = planner.build_steps(plan, inputs)
        explanation = planner.explain_plan(plan, steps)
        assert "Remediation Plan" in explanation
        assert "LOW" in explanation
        assert "Note: This plan is advisory-only" in explanation
