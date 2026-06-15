import uuid

import pytest
from app.models.core.admin_action_log import AdminActionLog
from app.services.operations.remediation.audit_events import (
    log_remediation_plan_proposed,
    log_remediation_step_proposed,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestRemediationAuditEvents:
    async def test_log_plan_proposed(self, session: AsyncSession):
        client_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        await log_remediation_plan_proposed(session, client_id, plan_id, "test_plan")
        await session.commit()

        stmt = select(AdminActionLog).where(
            AdminActionLog.action == "ops_remediation:remediation_plan_proposed"
        )
        result = await session.execute(stmt)
        entry = result.scalars().one()
        assert entry.payload_json["plan_id"] == str(plan_id)
        assert entry.payload_json["advisory_only"] is True

    async def test_log_step_proposed(self, session: AsyncSession):
        client_id = uuid.uuid4()
        step_id = uuid.uuid4()
        await log_remediation_step_proposed(session, client_id, step_id, "containment")
        await session.commit()

        stmt = select(AdminActionLog).where(
            AdminActionLog.action == "ops_remediation:remediation_step_proposed"
        )
        result = await session.execute(stmt)
        entry = result.scalars().one()
        assert entry.payload_json["step_id"] == str(step_id)
        assert entry.payload_json["action_type"] == "containment"
