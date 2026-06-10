import uuid

import pytest
from app.models.core.admin_action_log import AdminActionLog
from app.services.operations.remediation_execution.audit_events import (
    log_remediation_execution_started,
    log_remediation_kill_switch_updated,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestRemediationExecutionAuditEvents:
    async def test_log_exec_started(self, session: AsyncSession):
        client_id = uuid.uuid4()
        exec_id = uuid.uuid4()
        await log_remediation_execution_started(session, client_id, exec_id)
        await session.commit()
        
        stmt = select(AdminActionLog).where(AdminActionLog.action == "ops_remediation_exec:remediation_execution_started")
        result = await session.execute(stmt)
        entry = result.scalars().one()
        assert entry.payload_json["execution_id"] == str(exec_id)

    async def test_log_ks_updated(self, session: AsyncSession):
        client_id = uuid.uuid4()
        await log_remediation_kill_switch_updated(session, client_id, True, "Security breach")
        await session.commit()
        
        stmt = select(AdminActionLog).where(AdminActionLog.action == "ops_remediation_exec:remediation_kill_switch_updated")
        result = await session.execute(stmt)
        entry = result.scalars().one()
        assert entry.payload_json["enabled"] is True
        assert entry.payload_json["reason"] == "Security breach"
