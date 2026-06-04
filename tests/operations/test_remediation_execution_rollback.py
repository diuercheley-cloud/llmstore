from app.services.operations.remediation_execution.rollback import (
    RemediationRollbackPlanningService,
)


class TestRemediationExecutionRollback:
    def test_build_rollback_plan_reverses_order(self):
        service = RemediationRollbackPlanningService()
        steps = [
            {"action_type": "a1", "target_domain": "d1", "target_ref": "r1", "description": "desc1"},
            {"action_type": "a2", "target_domain": "d2", "target_ref": "r2", "description": "desc2"}
        ]
        rb_plan = service.build_rollback_plan({}, steps)
        rb_steps = rb_plan["rollback_steps_json"]
        assert len(rb_steps) == 2
        assert rb_steps[0]["action_type"] == "rollback_a2"
        assert rb_steps[1]["action_type"] == "rollback_a1"

    def test_validate_rollback_plan(self):
        service = RemediationRollbackPlanningService()
        assert service.validate_rollback_plan({"rollback_steps_json": [1]}) is True
        assert service.validate_rollback_plan({"rollback_steps_json": []}) is False
