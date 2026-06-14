import uuid
import pytest
from datetime import timedelta
from app.core.time import utc_now
from app.models.operations.remediation_planning import RemediationPlan, RemediationStep, RemediationApprovalRequirement
from app.models.operations.remediation_execution import RemediationExecution, RemediationExecutionStep
from app.models.governance.human_governance import CriticalApproval
from app.models.core.admin_action_log import AdminActionLog
from app.services.operations.remediation_execution.executor import ApprovalGatedRemediationExecutor
from app.services.operations.remediation_execution.action_registry import RemediationActionRegistry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import pytest_asyncio
from httpx import AsyncClient

@pytest_asyncio.fixture(autouse=True)
async def ensure_execution_tables(session: AsyncSession):
    import app.models.operations
    import app.models.governance.human_governance
    import app.models.core.admin_action_log
    from app.db.base import Base
    
    engine = session.bind
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@pytest.mark.asyncio
class TestRemediationGovernance:
    async def _setup_plan(self, session: AsyncSession, client_id: uuid.UUID, requires_approval=True):
        plan = RemediationPlan(
            client_id=client_id, plan_type="test", source_type="test", source_ref="ref",
            risk_level="high", blast_radius="medium", requires_approval=requires_approval,
            input_hash=str(uuid.uuid4()), immutable_hash=str(uuid.uuid4())
        )
        session.add(plan)
        await session.flush()
        
        step = RemediationStep(
            client_id=client_id, plan_id=plan.id, step_order=1, action_type="restart_service",
            target_domain="compute", target_ref="srv-1", description="desc", expected_effect="effect",
            immutable_hash=str(uuid.uuid4())
        )
        session.add(step)
        
        if requires_approval:
            req = RemediationApprovalRequirement(
                client_id=client_id, plan_id=plan.id, approval_scope="execution",
                required_role="ops_admin", reason="High risk", immutable_hash=str(uuid.uuid4())
            )
            session.add(req)
            
        await session.commit()
        return plan, [step]

    async def test_execution_without_approval_fails(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan, steps = await self._setup_plan(session, client_id, requires_approval=True)
        
        executor = ApprovalGatedRemediationExecutor()
        execution = await executor.prepare_execution(session, plan, steps, dry_run=False)
        await session.commit()
        
        # Execute without approval in DB
        result = await executor.execute(session, execution, plan, steps, [], None)
        assert result["status"] == "blocked"
        assert "Missing required approvals" in result["reasons"][0]
        
        # Verify status in DB
        await session.refresh(execution)
        assert execution.status == "blocked"

    async def test_execution_with_valid_approval_succeeds(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan, steps = await self._setup_plan(session, client_id, requires_approval=True)
        
        executor = ApprovalGatedRemediationExecutor()
        execution = await executor.prepare_execution(session, plan, steps, requested_by="admin1", dry_run=False)
        await session.commit()
        
        # Insert approval
        approval = CriticalApproval(
            action_type="ops_remediation_execution",
            description="Approve remediation",
            status="approved",
            requested_by="admin1",
            decided_by="manager1",
            decided_at=utc_now(),
            expires_at=utc_now() + timedelta(hours=1),
            payload={"plan_id": str(plan.id)}
        )
        session.add(approval)
        await session.commit()
        
        result = await executor.execute(session, execution, plan, steps, [], None)
        assert result["status"] == "succeeded"
        
        # Verify execution record
        await session.refresh(execution)
        assert execution.status == "succeeded"
        assert execution.approved_by == "manager1"
        assert execution.started_at is not None
        assert execution.completed_at is not None
        
        # Verify step record
        stmt = select(RemediationExecutionStep).where(RemediationExecutionStep.execution_id == execution.id)
        exec_step = (await session.execute(stmt)).scalar_one()
        assert exec_step.execution_status == "success"
        assert exec_step.started_at is not None
        assert exec_step.completed_at is not None
        assert "restarted successfully" in exec_step.output_summary

    async def test_dry_run_no_approval_required(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan, steps = await self._setup_plan(session, client_id, requires_approval=True)
        
        executor = ApprovalGatedRemediationExecutor()
        execution = await executor.prepare_execution(session, plan, steps, dry_run=True)
        await session.commit()
        
        # Dry run should pass even without approval in DB
        result = await executor.execute(session, execution, plan, steps, [], None)
        assert result["status"] == "dry_run_completed"
        
        await session.refresh(execution)
        assert execution.status == "dry_run_completed"

    async def test_step_failure_persists_status(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan, steps = await self._setup_plan(session, client_id, requires_approval=False)
        
        # Force a failure by using an unregistered action or a failing one
        steps[0].action_type = "invalid_action"
        await session.commit()
        
        executor = ApprovalGatedRemediationExecutor()
        execution = await executor.prepare_execution(session, plan, steps, dry_run=False)
        await session.commit()
        
        result = await executor.execute(session, execution, plan, steps, [], None)
        assert result["status"] == "failed"
        assert "is not supported" in result["error_message"]
        
        await session.refresh(execution)
        assert execution.status == "failed"
        assert execution.error_code == "action_not_found"
        
        # Verify audit event for failure
        stmt = select(AdminActionLog).where(AdminActionLog.action == "ops_remediation_exec:remediation_failed")
        audit = (await session.execute(stmt)).scalar_one_or_none()
        assert audit is not None
        assert audit.payload_json["error_code"] == "action_not_found"

    async def test_idempotency_blocks_duplicate_preparation(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan, steps = await self._setup_plan(session, client_id, requires_approval=False)
        
        executor = ApprovalGatedRemediationExecutor()
        ik = "idempotency-key-1"
        
        e1 = await executor.prepare_execution(session, plan, steps, idempotency_key=ik)
        await session.commit()
        
        e2 = await executor.prepare_execution(session, plan, steps, idempotency_key=ik)
        assert e1.id == e2.id
        
        # Different idempotency key should create different execution (if plan/steps differ, but here we check IK first)
        # Actually our implementation checks IK first.
        ik2 = "idempotency-key-2"
        e3 = await executor.prepare_execution(session, plan, steps, idempotency_key=ik2)
        assert e1.id != e3.id
