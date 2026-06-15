import uuid

import pytest
from app.models.operations.remediation_planning import RemediationPlan, RemediationStep
from app.services.operations.remediation_execution.executor import ApprovalGatedRemediationExecutor
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestApprovalGatedRemediationExecutor:
    async def test_prepare_and_execute_dry_run(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan = RemediationPlan(
            client_id=client_id,
            plan_type="t",
            source_type="s",
            source_ref="r",
            risk_level="low",
            blast_radius="low",
            input_hash="ih",
            immutable_hash="ph",
        )
        session.add(plan)
        await session.flush()  # Ensure plan.id is populated

        step = RemediationStep(
            client_id=client_id,
            plan_id=plan.id,
            step_order=1,
            action_type="a",
            target_domain="d",
            target_ref="tr",
            description="desc",
            expected_effect="e",
            immutable_hash="sh",
        )
        session.add(step)
        await session.commit()

        executor = ApprovalGatedRemediationExecutor()
        execution = await executor.prepare_execution(session, plan, [step], dry_run=True)
        await session.commit()

        assert execution.status == "pending"

        result = await executor.execute(session, execution, plan, [step], [], None)
        assert result["status"] == "dry_run_completed"
        assert len(result["step_results"]) == 1

    async def test_execute_blocked_by_kill_switch(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan = RemediationPlan(
            client_id=client_id,
            plan_type="t2",
            source_type="s",
            source_ref="r",
            risk_level="low",
            blast_radius="low",
            input_hash="ih2",
            immutable_hash="ph2",
        )
        session.add(plan)
        await session.flush()

        step = RemediationStep(
            client_id=client_id,
            plan_id=plan.id,
            step_order=1,
            action_type="a",
            target_domain="d",
            target_ref="tr",
            description="desc",
            expected_effect="e",
            immutable_hash="sh2",
        )
        session.add(step)
        await session.commit()

        executor = ApprovalGatedRemediationExecutor()
        execution = await executor.prepare_execution(session, plan, [step], dry_run=True)

        class MockKS:
            def __init__(self):
                self.enabled = True

        result = await executor.execute(session, execution, plan, [step], [], MockKS())
        assert result["status"] == "blocked"
        assert "kill-switch" in result["reasons"][0].lower()
