import pytest
import uuid
import asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentTool, AgentToolInvocation, AgentToolVersion, AgentRegistryEntry
from app.services.agents.tool_registry import create_tool, get_tool, update_tool, add_safety_review
from app.services.agents.tool_policy import evaluate_tool_policy
from app.services.agents.tool_executor import execute_tool, hash_payload
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def setup_test_flags(monkeypatch):
    """Sets initial settings values for flags to ensure test stability."""
    monkeypatch.setenv("AGENT_TOOL_REGISTRY_ENABLED", "true")
    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_DESTRUCTIVE_TOOLS_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_tool_registration_validation(admin_client: AsyncClient, admin_token_headers, session: AsyncSession):
    # 1. Tool sem schema falha
    payload_no_input = {
        "name": "no_input_schema_tool",
        "category": "retrieval",
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30
    }
    resp = await admin_client.post("/admin/agent-tools", json=payload_no_input, headers=admin_token_headers)
    assert resp.status_code == 400
    assert "input_schema_json" in resp.json()["detail"]

    payload_no_output = {
        "name": "no_output_schema_tool",
        "category": "retrieval",
        "input_schema_json": {"type": "object"},
        "timeout_seconds": 30
    }
    resp = await admin_client.post("/admin/agent-tools", json=payload_no_output, headers=admin_token_headers)
    assert resp.status_code == 400
    assert "output_schema_json" in resp.json()["detail"]

    # 2. Tool external_api deve declarar data_boundary
    payload_ext_no_boundary = {
        "name": "external_tool_no_boundary",
        "category": "external_api",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30
    }
    resp = await admin_client.post("/admin/agent-tools", json=payload_ext_no_boundary, headers=admin_token_headers)
    assert resp.status_code == 400
    assert "data_boundary" in resp.json()["detail"]

    # 3. Tool write/destructive exige approval por padrão
    payload_write = {
        "name": "write_tool_default_approval",
        "category": "database_write",
        "side_effect_level": "write",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30
    }
    resp = await admin_client.post("/admin/agent-tools", json=payload_write, headers=admin_token_headers)
    assert resp.status_code == 201
    assert resp.json()["requires_approval"] is True

    # 4. Tool shell_command é disabled por padrão
    payload_shell = {
        "name": "shell_tool_default_disabled",
        "category": "shell_command",
        "side_effect_level": "destructive",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30
    }
    resp = await admin_client.post("/admin/agent-tools", json=payload_shell, headers=admin_token_headers)
    assert resp.status_code == 201
    assert resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_tool_policy_and_experimental_agents(session: AsyncSession):
    # Register tool without dry_run support
    tool_no_dry = await create_tool(session, {
        "name": "no_dry_run_tool",
        "category": "retrieval",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "dry_run_supported": False
    })

    # Register tool with dry_run support
    tool_with_dry = await create_tool(session, {
        "name": "dry_run_supported_tool",
        "category": "retrieval",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "dry_run_supported": True
    })

    # Experimental Agent Registry entry
    exp_agent = AgentRegistryEntry(
        agent_id=uuid.uuid4(),
        name="Experimental Tester Agent",
        supported_surface_status="experimental"
    )
    session.add(exp_agent)
    await session.commit()

    # Experimental agent cannot use tool without dry_run
    dec1 = await evaluate_tool_policy(session, tool_no_dry, exp_agent)
    assert dec1.allowed is False
    assert dec1.reason == "experimental_agent_restricted_no_dry_run"

    # Experimental agent can use tool with dry_run
    dec2 = await evaluate_tool_policy(session, tool_with_dry, exp_agent)
    assert dec2.allowed is True


@pytest.mark.asyncio
async def test_destructive_tool_requires_approval_and_safety_review(session: AsyncSession):
    # Register destructive tool
    tool = await create_tool(session, {
        "name": "destructive_admin_tool",
        "category": "admin_operation",
        "side_effect_level": "destructive",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "requires_approval": True
    })

    # Evaluate policy: requires human approval
    dec = await evaluate_tool_policy(session, tool)
    assert dec.allowed is True
    assert dec.requires_approval is True
    assert dec.reason == "approval_required"

    # Try executing: fails because it requires approval
    with pytest.raises(ValueError, match="requires human approval|approval_required"):
        await execute_tool(session, tool, parameters={}, is_dry_run=False)

    # Perform safety review approval
    await add_safety_review(session, tool.id, reviewer="sec-admin", decision="approved")

    # Refresh tool to see change in requires_approval
    await session.refresh(tool)
    assert tool.requires_approval is False

    # Policy evaluation should now allow execution without approval
    dec_after = await evaluate_tool_policy(session, tool)
    assert dec_after.allowed is True
    assert dec_after.requires_approval is False


@pytest.mark.asyncio
async def test_disabled_tool_execution(session: AsyncSession):
    # Register disabled tool
    tool = await create_tool(session, {
        "name": "disabled_test_tool",
        "category": "retrieval",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 30,
        "enabled": False
    })

    # Policy denies
    dec = await evaluate_tool_policy(session, tool)
    assert dec.allowed is False
    assert dec.reason == "tool_disabled"

    # Execution denies
    with pytest.raises(ValueError, match="tool_disabled"):
        await execute_tool(session, tool, parameters={})


@pytest.mark.asyncio
async def test_timeout_is_enforced(session: AsyncSession):
    # Register tool with 1 second timeout
    tool = await create_tool(session, {
        "name": "timeout_test_tool",
        "category": "retrieval",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 1
    })

    async def long_running_tool(**kwargs):
        await asyncio.sleep(3)
        return {"status": "done"}

    # Execution should raise TimeoutError
    with pytest.raises(asyncio.TimeoutError):
        await execute_tool(session, tool, parameters={}, tool_callable=long_running_tool)

    # Verify invocation recorded in database as failed due to timeout
    stmt = select(AgentToolInvocation).where(AgentToolInvocation.agent_tool_id == tool.id)
    result = await session.execute(stmt)
    invocations = result.scalars().all()
    assert len(invocations) == 1
    assert invocations[0].status == "failed"
    assert "TimeoutError" in invocations[0].error_message or "timeout" in invocations[0].error_message.lower()


@pytest.mark.asyncio
async def test_audited_invocation_hashes_input_and_output(session: AsyncSession):
    tool = await create_tool(session, {
        "name": "audit_hash_tool",
        "category": "retrieval",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 10
    })

    async def my_tool(param1, param2):
        return {"result": f"processed_{param1}_{param2}"}

    params = {"param1": "hello", "param2": "world"}
    expected_input_hash = hash_payload(params)

    output = await execute_tool(session, tool, parameters=params, tool_callable=my_tool)
    expected_output_hash = hash_payload(output)

    # Verify DB entry
    stmt = select(AgentToolInvocation).where(AgentToolInvocation.agent_tool_id == tool.id)
    result = await session.execute(stmt)
    inv = result.scalars().first()

    assert inv is not None
    assert inv.status == "success"
    assert inv.input_hash == expected_input_hash
    assert inv.output_hash == expected_output_hash
    # Input bruto não aparece nos logs/banco:
    assert not hasattr(inv, "input_json")
    assert not hasattr(inv, "output_json")


@pytest.mark.asyncio
async def test_dry_run_no_side_effects(session: AsyncSession):
    tool = await create_tool(session, {
        "name": "dry_run_test_tool",
        "category": "retrieval",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 10,
        "dry_run_supported": True
    })

    called = False
    async def my_tool():
        nonlocal called
        called = True
        return {"status": "actual_run"}

    output = await execute_tool(session, tool, parameters={}, is_dry_run=True, tool_callable=my_tool)
    assert not called
    assert output["status"] == "dry_run_success"

    # Check invocation in DB
    stmt = select(AgentToolInvocation).where(AgentToolInvocation.agent_tool_id == tool.id)
    result = await session.execute(stmt)
    inv = result.scalars().first()
    assert inv is not None
    assert inv.status == "dry_run"
    assert inv.is_dry_run is True


@pytest.mark.asyncio
async def test_rollback_compensation_execution(session: AsyncSession):
    tool = await create_tool(session, {
        "name": "rollback_test_tool",
        "category": "database_write",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 10,
        "rollback_supported": True
    })

    async def failing_tool():
        raise RuntimeError("Something went wrong")

    rollback_called = False
    async def rollback_callback():
        nonlocal rollback_called
        rollback_called = True

    with pytest.raises(RuntimeError):
        await execute_tool(
            session, 
            tool, 
            parameters={}, 
            tool_callable=failing_tool, 
            rollback_callable=rollback_callback
        )

    assert rollback_called

    # Check invocation
    stmt = select(AgentToolInvocation).where(AgentToolInvocation.agent_tool_id == tool.id)
    result = await session.execute(stmt)
    inv = result.scalars().first()
    assert inv is not None
    assert inv.status == "rolled_back"


@pytest.mark.asyncio
async def test_feature_flags_execution_gate(session: AsyncSession, monkeypatch):
    tool = await create_tool(session, {
        "name": "ff_gate_tool",
        "category": "retrieval",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 10
    })

    # Disable execution flag
    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "false")
    get_settings.cache_clear()

    async def my_tool():
        return {"status": "ok"}

    with pytest.raises(ValueError, match="Tool execution is disabled by feature flag"):
        await execute_tool(session, tool, parameters={}, tool_callable=my_tool)

    # Re-enable flag
    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "true")
    get_settings.cache_clear()

    res = await execute_tool(session, tool, parameters={}, tool_callable=my_tool)
    assert res == {"status": "ok"}


@pytest.mark.asyncio
async def test_feature_flags_destructive_gate(session: AsyncSession, monkeypatch):
    # Destructive tool
    tool = await create_tool(session, {
        "name": "destructive_ff_tool",
        "category": "shell_command",
        "side_effect_level": "destructive",
        "input_schema_json": {"type": "object"},
        "output_schema_json": {"type": "object"},
        "timeout_seconds": 10,
        "requires_approval": False, # bypass approval for test focus
        "enabled": True
    })

    # Disable destructive tools
    monkeypatch.setenv("AGENT_DESTRUCTIVE_TOOLS_ENABLED", "false")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="Destructive tool execution is disabled by feature flag"):
        await execute_tool(session, tool, parameters={})

    # Enable destructive tools
    monkeypatch.setenv("AGENT_DESTRUCTIVE_TOOLS_ENABLED", "true")
    get_settings.cache_clear()

    # No callable but execution is enabled -> returns dummy mock success without raising ff exception
    res = await execute_tool(session, tool, parameters={})
    assert res["status"] == "success"


@pytest.mark.asyncio
async def test_api_admin_routing_gates(admin_client: AsyncClient, admin_token_headers, monkeypatch):
    # When registry flag is disabled
    monkeypatch.setenv("AGENT_TOOL_REGISTRY_ENABLED", "false")
    get_settings.cache_clear()

    resp = await admin_client.get("/admin/agent-tools", headers=admin_token_headers)
    assert resp.status_code == 400
    assert "Agent tool registry is disabled" in resp.json()["detail"]

    # When registry flag is enabled
    monkeypatch.setenv("AGENT_TOOL_REGISTRY_ENABLED", "true")
    get_settings.cache_clear()

    resp = await admin_client.get("/admin/agent-tools", headers=admin_token_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
