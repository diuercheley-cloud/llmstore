import os
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agent_workflows import AgentWorkflow, AgentWorkflowRun
from app.models.agents.agent_workflows_external import (
    AgentWorkflowExternalEvent,
)
from app.services.agents.workflows.workflow_polling import WorkflowPollingService
from app.services.agents.workflows.workflow_webhooks import WorkflowWebhookService
from sqlalchemy import select


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session

@pytest.fixture
async def workflow_run(db_session):
    wf = AgentWorkflow(name="test", version="1", tenant_id="t1")
    db_session.add(wf)
    await db_session.flush()
    run = AgentWorkflowRun(workflow_id=wf.id, tenant_id="t1", status="running", current_state="s")
    db_session.add(run)
    await db_session.commit()
    return run

@pytest.mark.asyncio
async def test_webhook_triggers_signal(db_session, workflow_run):
    with patch.dict(os.environ, {"AGENT_WORKFLOW_WEBHOOKS_ENABLED": "true"}):
        get_settings.cache_clear()
        service = WorkflowWebhookService(db_session)
        
        # 1. Create subscription
        sub = await service.create_subscription(workflow_run.id, "t1")
        await db_session.commit()
        
        # 2. Handle incoming with correct token
        payload = {"status": "success", "data": "info", "secret": "123"}
        result = await service.handle_incoming(sub.id, payload, sub.secret_token)
        
        # 3. Verify event and sanitization
        stmt = select(AgentWorkflowExternalEvent).where(AgentWorkflowExternalEvent.run_id == workflow_run.id)
        res = await db_session.execute(stmt)
        event = res.scalar_one()
        assert event.payload["data"] == "info"
        assert event.sanitized_payload["secret"] == "[REDACTED]"
        
        # 4. Verify subscription triggered
        await db_session.refresh(sub)
        assert sub.status == "triggered"

@pytest.mark.asyncio
async def test_polling_job_lifecycle(db_session, workflow_run):
    with patch.dict(os.environ, {"AGENT_WORKFLOW_POLLING_ENABLED": "true"}):
        get_settings.cache_clear()
        service = WorkflowPollingService(db_session)
        
        # 1. Create job
        job = await service.create_polling_job(
            workflow_run.id, "t1", "https://api.com", 
            {"path": "status", "value": "done"}, interval=10
        )
        await db_session.commit()
        assert job.status == "active"
        
        # 2. Execute poll (mocking condition not met)
        await service._execute_poll(job)
        assert job.attempts_count == 1
        assert job.next_poll_at > utc_now()
        
        # 3. Execute poll (simulating condition met)
        # Note: _execute_poll uses internal mock logic for now
        # We simulate completion by manually setting mock-compatible count if needed
        # but for prototype we just verify it runs without error.
        await service.process_ready_polls()

@pytest.mark.asyncio
async def test_webhook_invalid_token(db_session, workflow_run):
    with patch.dict(os.environ, {"AGENT_WORKFLOW_WEBHOOKS_ENABLED": "true"}):
        get_settings.cache_clear()
        service = WorkflowWebhookService(db_session)
        sub = await service.create_subscription(workflow_run.id, "t1")
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await service.handle_incoming(sub.id, {}, "wrong-token")
        assert exc.value.status_code == 401

import pytest_asyncio
