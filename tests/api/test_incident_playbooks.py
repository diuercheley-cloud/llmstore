import uuid
import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.agents.agents import AgentDefinition, AgentTool, AgentIncident

@pytest_asyncio.fixture(autouse=True)
async def setup_incident_api_db(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_run_playbook_api_unauthorized(async_client: AsyncClient, admin_token_headers):
    # Seed DB with a test incident first so lookup succeeds and moves to permission verification
    agent_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    tool_name = f"api_test_tool_unauth_{uuid.uuid4().hex[:8]}"

    async with SessionLocal() as db:
        agent = AgentDefinition(
            id=agent_id,
            name="API Incident Agent Unauth",
            version="1.0.0",
            description="Agent for API testing",
            instructions="Handle incident",
            model_id="gpt-4",
            owner="admin",
            tenant_id="default",
        )
        tool = AgentTool(
            id=uuid.uuid4(),
            name=tool_name,
            category="filesystem_safe",
            input_schema_json={},
            output_schema_json={},
            enabled=True,
        )
        incident = AgentIncident(
            id=incident_id,
            tenant_id="default",
            agent_id=agent_id,
            incident_type="tool_cascade_failure",
            status="open",
            title="API Incident Unauth",
            details_json={"tool_name": tool_name},
        )
        db.add(agent)
        db.add(tool)
        db.add(incident)
        await db.commit()

    # Call with unauthorized performed_by value -> should raise 400 permission denied in the executor
    resp = await async_client.post(
        f"/admin/agents/incidents/{incident_id}/run-playbook",
        headers=admin_token_headers,
        json={
            "playbook_id": "tool-cascade-failure",
            "performed_by": "unauthorized_user",
            "confirmation": True
        }
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "permission" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_run_playbook_api_success_flow(async_client: AsyncClient, admin_token_headers):
    # Seed DB with test agent, unique tool, and incident
    agent_id = uuid.uuid4()
    incident_id = uuid.uuid4()
    tool_name = f"api_test_tool_{uuid.uuid4().hex[:8]}"

    async with SessionLocal() as db:
        agent = AgentDefinition(
            id=agent_id,
            name="API Incident Agent",
            version="1.0.0",
            description="Agent for API testing",
            instructions="Handle incident",
            model_id="gpt-4",
            owner="admin",
            tenant_id="default",
        )
        tool = AgentTool(
            id=uuid.uuid4(),
            name=tool_name,
            category="filesystem_safe",
            input_schema_json={},
            output_schema_json={},
            enabled=True,
        )
        incident = AgentIncident(
            id=incident_id,
            tenant_id="default",
            agent_id=agent_id,
            incident_type="tool_cascade_failure",
            status="open",
            title="API Incident",
            details_json={"tool_name": tool_name},
        )
        db.add(agent)
        db.add(tool)
        db.add(incident)
        await db.commit()

    # 1. Execute playbook with dry_run = True
    resp = await async_client.post(
        f"/admin/agents/incidents/{incident_id}/run-playbook",
        headers=admin_token_headers,
        json={
            "playbook_id": "tool-cascade-failure",
            "performed_by": "admin_write",
            "confirmation": True,
            "dry_run": True
        }
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["actions"]) == 1
    assert data["actions"][0]["dry_run"] is True
    assert data["actions"][0]["changed"] is False
    assert data["after"]["incident_status"] == "open"

    # Verify state in DB remains unchanged
    async with SessionLocal() as db:
        t = await db.get(AgentTool, tool.id)
        assert t.enabled is True
        inc = await db.get(AgentIncident, incident_id)
        assert inc.status == "open"

    # 2. Execute playbook with dry_run = False
    resp2 = await async_client.post(
        f"/admin/agents/incidents/{incident_id}/run-playbook",
        headers=admin_token_headers,
        json={
            "playbook_id": "tool-cascade-failure",
            "performed_by": "admin_write",
            "confirmation": True,
            "dry_run": False
        }
    )
    assert resp2.status_code == status.HTTP_200_OK
    data2 = resp2.json()
    assert len(data2["actions"]) == 1
    assert data2["actions"][0]["dry_run"] is False
    assert data2["actions"][0]["changed"] is True
    assert data2["after"]["incident_status"] == "resolved"

    # Verify state in DB has changed
    async with SessionLocal() as db:
        t = await db.get(AgentTool, tool.id)
        assert t.enabled is False
        inc = await db.get(AgentIncident, incident_id)
        assert inc.status == "resolved"
        assert inc.resolved_by == "admin_write"
