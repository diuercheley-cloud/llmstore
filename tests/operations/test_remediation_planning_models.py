import uuid

import pytest
from app.models.operations.remediation_planning import (
    RemediationApprovalRequirement,
    RemediationPlan,
    RemediationPlanReceipt,
    RemediationStep,
    compute_deterministic_hash,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TestRemediationDeterministicHash:
    def test_deterministic_same_input(self):
        fields = {"client_id": str(uuid.uuid4()), "source": "test"}
        h1 = compute_deterministic_hash(fields=fields)
        h2 = compute_deterministic_hash(fields=fields)
        assert h1 == h2

    def test_deterministic_different_input(self):
        h1 = compute_deterministic_hash(fields={"a": 1})
        h2 = compute_deterministic_hash(fields={"a": 2})
        assert h1 != h2

@pytest.mark.asyncio
class TestRemediationPlanningModels:
    async def test_create_remediation_plan(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan = RemediationPlan(
            client_id=client_id,
            plan_type="test_plan",
            source_type="forecast",
            source_ref="forecast_123",
            risk_level="high",
            blast_radius="medium",
            input_hash="input_h",
            immutable_hash="immut_h"
        )
        session.add(plan)
        await session.commit()

        result = await session.execute(
            select(RemediationPlan).where(RemediationPlan.client_id == client_id)
        )
        saved = result.scalars().one()
        assert saved.plan_type == "test_plan"
        assert saved.advisory_only is True
        assert saved.dry_run is True
        assert saved.status == "proposed"

    async def test_create_remediation_step(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        
        # Mock plan for FK
        plan = RemediationPlan(
            id=plan_id,
            client_id=client_id,
            plan_type="test",
            source_type="test",
            source_ref="test",
            risk_level="low",
            blast_radius="low",
            input_hash="ih",
            immutable_hash="ph"
        )
        session.add(plan)
        
        step = RemediationStep(
            client_id=client_id,
            plan_id=plan_id,
            step_order=1,
            action_type="containment",
            target_domain="auth",
            target_ref="auth_breaker",
            description="Isolate auth",
            expected_effect="Isolated",
            immutable_hash="step_h"
        )
        session.add(step)
        await session.commit()

        result = await session.execute(
            select(RemediationStep).where(RemediationStep.plan_id == plan_id)
        )
        saved = result.scalars().one()
        assert saved.action_type == "containment"
        assert saved.advisory_only is True

    async def test_create_approval_requirement(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        
        plan = RemediationPlan(
            id=plan_id,
            client_id=client_id,
            plan_type="test",
            source_type="test",
            source_ref="test",
            risk_level="low",
            blast_radius="low",
            input_hash="ih2",
            immutable_hash="ph2"
        )
        session.add(plan)
        
        req = RemediationApprovalRequirement(
            client_id=client_id,
            plan_id=plan_id,
            approval_scope="executive",
            required_role="director",
            reason="High risk",
            immutable_hash="req_h"
        )
        session.add(req)
        await session.commit()

        result = await session.execute(
            select(RemediationApprovalRequirement).where(RemediationApprovalRequirement.plan_id == plan_id)
        )
        saved = result.scalars().one()
        assert saved.approval_scope == "executive"
        assert saved.required_role == "director"

    async def test_create_receipt(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        
        plan = RemediationPlan(
            id=plan_id,
            client_id=client_id,
            plan_type="test",
            source_type="test",
            source_ref="test",
            risk_level="low",
            blast_radius="low",
            input_hash="ih3",
            immutable_hash="ph3"
        )
        session.add(plan)
        
        receipt = RemediationPlanReceipt(
            client_id=client_id,
            plan_id=plan_id,
            receipt_type="proposal",
            payload_hash="pay_h",
            immutable_hash="rec_h",
            signature="sig_h"
        )
        session.add(receipt)
        await session.commit()

        result = await session.execute(
            select(RemediationPlanReceipt).where(RemediationPlanReceipt.plan_id == plan_id)
        )
        saved = result.scalars().one()
        assert saved.receipt_type == "proposal"
        assert saved.signature == "sig_h"
