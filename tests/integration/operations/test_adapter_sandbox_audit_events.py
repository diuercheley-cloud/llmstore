import uuid

import pytest
from app.models.core.admin_action_log import AdminActionLog
from app.services.operations.adapter_sandbox.audit_events import (
    log_adapter_manifest_registered,
    log_adapter_sandbox_run_completed,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestAdapterSandboxAuditEvents:
    async def test_log_manifest_registered(self, session: AsyncSession):
        client_id = uuid.uuid4()
        manifest_id = uuid.uuid4()
        await log_adapter_manifest_registered(session, client_id, manifest_id, "test_adapter")
        await session.commit()

        stmt = select(AdminActionLog).where(
            AdminActionLog.action == "ops_adapter_sandbox:adapter_manifest_registered"
        )
        result = await session.execute(stmt)
        entry = result.scalars().one()
        assert entry.payload_json["manifest_id"] == str(manifest_id)

    async def test_log_run_completed(self, session: AsyncSession):
        client_id = uuid.uuid4()
        run_id = uuid.uuid4()
        await log_adapter_sandbox_run_completed(session, client_id, run_id, "simulated")
        await session.commit()

        stmt = select(AdminActionLog).where(
            AdminActionLog.action == "ops_adapter_sandbox:adapter_sandbox_run_completed"
        )
        result = await session.execute(stmt)
        entry = result.scalars().one()
        assert entry.payload_json["run_id"] == str(run_id)
        assert entry.payload_json["status"] == "simulated"
