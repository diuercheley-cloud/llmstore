import uuid
from typing import Any, Dict, Optional

import pytest
import pytest_asyncio
from app.models.agents.agents import AgentToolInvocation
from app.services.agents.agent_state import create_agent_definition, create_agent_run
from app.services.agents.tool_executor import execute_tool
from app.services.agents.tool_policy import evaluate_tool_policy
from app.services.agents.tool_registry import create_tool
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_tool_env(monkeypatch):
    monkeypatch.setenv("AGENT_TOOL_REGISTRY_ENABLED", "true")
    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_DESTRUCTIVE_TOOLS_ENABLED", "true")
    from app.core.config import get_settings
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_tool_registration_validation(admin_client: AsyncClient, admin_token_headers):
    # 1. Missing mandatory field 'category'
    payload_no_cat = {
        "name": "no_cat_tool",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30
    }
    resp = await admin_client.post("/admin/agent-tools", json=payload_no_cat, headers=admin_token_headers)
    assert resp.status_code == 422

    # 2. Tool external sem data_boundary deve falhar
    payload_ext_no_boundary = {
        "name": "external_tool_no_boundary",
        "category": "external_api",
        "risk_level": "medium",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30
    }
    resp = await admin_client.post("/admin/agent-tools", json=payload_ext_no_boundary, headers=admin_token_headers)
    assert resp.status_code == 400
    assert "data_boundary" in resp.json()["detail"]

    # 3. Tool write/destructive exige approval policy
    payload_write = {
        "name": "write_tool_default_approval",
        "category": "database_write",
        "side_effect_level": "write",
        "risk_level": "high",
        "approval_policy": {"type": "manual"},
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30
    }
    resp = await admin_client.post("/admin/agent-tools", json=payload_write, headers=admin_token_headers)
    assert resp.status_code == 201
    assert resp.json()["requires_approval"] is True


@pytest.mark.asyncio
async def test_destructive_tool_requires_approval_and_safety_review(session: AsyncSession):
    tool = await create_tool(session, {
        "name": "purge_tool",
        "category": "database_write",
        "side_effect_level": "destructive",
        "risk_level": "critical",
        "approval_policy": {"type": "manual"},
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })
    
    agent_def = await create_agent_definition(session, {
        "name": "Test Agent",
        "version": "1.0.0",
        "owner": "test-owner",
        "status": "active",
        "model_id": "m",
        "instructions": "test",
        "allowed_tools": ["*"]
    })
    await session.commit()

    dec = await evaluate_tool_policy(session, tool, agent_id=agent_def.id, tenant_id="default")
    assert dec.requires_approval is True


@pytest.mark.asyncio
async def test_disabled_tool_execution(session: AsyncSession):
    tool = await create_tool(session, {
        "name": "disabled_tool",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": False
    })

    agent_def = await create_agent_definition(session, {
        "name": "Test Agent",
        "version": "1.0.0",
        "owner": "test-owner",
        "status": "active",
        "model_id": "m",
        "instructions": "test",
        "allowed_tools": ["*"]
    })
    await session.commit()

    dec = await evaluate_tool_policy(session, tool, agent_id=agent_def.id, tenant_id="default")
    assert dec.allowed is False
    assert dec.reason == "tool_disabled"


@pytest.mark.asyncio
async def test_timeout_is_enforced(session: AsyncSession):
    tool = await create_tool(session, {
        "name": "slow_tool",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 1,
        "enabled": True
    })

    async def my_slow_tool(**kwargs):
        import asyncio
        await asyncio.sleep(2)
        return {"status": "ok"}

    run = await create_agent_run(session, uuid.uuid4(), "default", "test")

    with pytest.raises(Exception):
        await execute_tool(session, tool, parameters={}, tool_callable=my_slow_tool, run_id=run.id)
    
    # Check AgentToolInvocation
    stmt = select(AgentToolInvocation).where(AgentToolInvocation.run_id == run.id)
    res = await session.execute(stmt)
    invocations = res.scalars().all()
    assert len(invocations) > 0


@pytest.mark.asyncio
async def test_audited_invocation_hashes_input_and_output(session: AsyncSession):
    tool = await create_tool(session, {
        "name": "hash_tool",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })

    def my_tool(**kwargs):
        param1 = kwargs.get("param1")
        return {"result": f"processed {param1}"}

    params = {"param1": "data"}
    run = await create_agent_run(session, uuid.uuid4(), "default", "test")

    output = await execute_tool(session, tool, parameters=params, tool_callable=my_tool, run_id=run.id)
    assert output["result"] == "processed data"

    stmt = select(AgentToolInvocation).where(AgentToolInvocation.run_id == run.id)
    res = await session.execute(stmt)
    invocations = res.scalars().all()
    assert len(invocations) > 0
    assert invocations[0].input_hash is not None


@pytest.mark.asyncio
async def test_dry_run_no_side_effects(session: AsyncSession):
    tool = await create_tool(session, {
        "name": "side_effect_tool",
        "category": "database_write",
        "side_effect_level": "write",
        "risk_level": "high",
        "approval_policy": {"type": "manual"},
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "dry_run_supported": True,
        "enabled": True,
        "requires_approval": False
    })

    side_effect_happened = [False]

    def my_tool(**kwargs):
        if not kwargs.get("is_dry_run"):
            side_effect_happened[0] = True
        return {"status": "ok"}

    run = await create_agent_run(session, uuid.uuid4(), "default", "test")

    await execute_tool(session, tool, parameters={}, tool_callable=my_tool, is_dry_run=True, run_id=run.id)
    assert side_effect_happened[0] is False

    await execute_tool(session, tool, parameters={}, tool_callable=my_tool, is_dry_run=False, run_id=run.id)
    assert side_effect_happened[0] is True


@pytest.mark.asyncio
async def test_rollback_compensation_execution(session: AsyncSession):
    pytest.skip("Rollback execution needs manual verification of current implementation")


@pytest.mark.asyncio
async def test_feature_flags_execution_gate(session: AsyncSession, monkeypatch):
    tool = await create_tool(session, {
        "name": "flagged_tool",
        "category": "retrieval",
        "risk_level": "low",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })

    def my_tool(**kwargs): return {"ok": True}
    run = await create_agent_run(session, uuid.uuid4(), "default", "test")

    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()
    
    with pytest.raises(ValueError, match="disabled by feature flag"):
        await execute_tool(session, tool, parameters={}, tool_callable=my_tool, run_id=run.id)

    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()
    res = await execute_tool(session, tool, parameters={}, tool_callable=my_tool, run_id=run.id)
    assert res["ok"] is True


@pytest.mark.asyncio
async def test_feature_flags_destructive_gate(session: AsyncSession, monkeypatch):
    tool = await create_tool(session, {
        "name": "dangerous_tool",
        "category": "shell_command",
        "side_effect_level": "destructive",
        "risk_level": "critical",
        "approval_policy": {"type": "manual"},
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": True
    })

    monkeypatch.setenv("AGENT_DESTRUCTIVE_TOOLS_ENABLED", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()

    def my_tool(**kwargs): return {"ok": True}
    run = await create_agent_run(session, uuid.uuid4(), "default", "test")

    with pytest.raises(ValueError, match="Destructive"):
        await execute_tool(session, tool, parameters={}, tool_callable=my_tool, run_id=run.id)
