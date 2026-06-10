import uuid

import pytest
from app.models.operations.remediation_execution import (
    RemediationExecution,
    RemediationKillSwitchState,
)
from app.models.operations.remediation_planning import RemediationPlan
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestRemediationExecutionModels:
    async def test_create_remediation_execution(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        
        # Mock plan
        plan = RemediationPlan(
            id=plan_id, client_id=client_id, plan_type="test", source_type="test",
            source_ref="ref", risk_level="low", blast_radius="low", input_hash="ih", immutable_hash="ph"
        )
        session.add(plan)
        
        execution = RemediationExecution(
            client_id=client_id,
            plan_id=plan_id,
            execution_mode="simulation",
            dry_run=True,
            status="pending",
            input_hash="exec_ih",
            immutable_hash="exec_ph"
        )
        session.add(execution)
        await session.commit()

        result = await session.execute(select(RemediationExecution).where(RemediationExecution.client_id == client_id))
        saved = result.scalars().one()
        assert saved.execution_mode == "simulation"
        assert saved.dry_run is True

    async def test_create_kill_switch_state(self, session: AsyncSession):
        client_id = uuid.uuid4()
        state = RemediationKillSwitchState(
            client_id=client_id,
            enabled=True,
            reason="Testing",
            immutable_hash="ks_h"
        )
        session.add(state)
        await session.commit()

        result = await session.execute(select(RemediationKillSwitchState).where(RemediationKillSwitchState.client_id == client_id))
        saved = result.scalars().one()
        assert saved.enabled is True
        assert saved.reason == "Testing"
