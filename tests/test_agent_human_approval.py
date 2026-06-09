import uuid
from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import (
    AgentApprovalPolicy,
    AgentApprovalRequest,
    AgentRun,
    AgentTool,
)
from app.services.agents import agent_runtime, agent_state
from app.services.agents.agent_executor import MockLLMProvider
from app.services.agents.human_approval import (
    check_all_expired_requests,
    sanitize_value,
)
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def setup_approval_flags(monkeypatch):
    """Setup environment flags for the human approval test suite."""
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_TOOL_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_DESTRUCTIVE_TOOLS_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_PLANE_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("AGENT_EXECUTOR_MOCK_MODE", "false")
    monkeypatch.setenv("AGENT_HUMAN_APPROVAL_ENABLED", "true")
    monkeypatch.setenv("AGENT_APPROVAL_REQUIRED_FOR_HIGH_RISK", "true")
    monkeypatch.setenv("AGENT_APPROVAL_TIMEOUT_SECONDS", "86400")
    monkeypatch.setenv("RBAC_ADMIN_ENABLED", "false")
    monkeypatch.setenv("ADMIN_SUPER_TOKEN", "super-token")
    monkeypatch.setenv("ADMIN_WRITE_TOKEN", "write-token")
    monkeypatch.setenv("ADMIN_READ_TOKEN", "read-token")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_high_risk_tool_triggers_approval_and_approves(
    admin_client: AsyncClient, session: AsyncSession
):
    # 1. Create an active agent definition
    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "HITL Agent",
            "version": "1.0.0",
            "instructions": "Execute destructive tools safely.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-xyz",
            "status": "active",
            "allowed_tools": ["destructive_tool"],
            "max_steps": 10,
            "max_runtime_seconds": 300,
            "risk_level": "high",
        }
    )

    # 2. Register the high risk tool in DB
    tool = AgentTool(
        name="destructive_tool",
        version="1.0.0",
        description="A highly critical destructive tool",
        category="filesystem_destructive",
        input_schema_json={"type": "object"},
        output_schema_json={"type": "object"},
        risk_level="high",
        side_effect_level="destructive",
        requires_approval=True,
        owner="tester",
        enabled=True,
    )
    session.add(tool)
    await session.commit()

    # 3. Setup mock responses
    llm_responses = [
        {
            "type": "tool_call",
            "tool_name": "destructive_tool",
            "tool_input": {
                "password": "my_password_123",
                "prompt": "delete root",
                "safe_param": "hello"
            }
        },
        {"type": "final", "output": "Job successfully completed after approval"}
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    # Mock tool execution return
    tool_calls = []
    async def mock_tool_runner(name, tool_input):
        tool_calls.append((name, tool_input))
        return {"status": "ok"}

    # 4. Start the run
    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-xyz",
        input_text="Delete resources.",
        llm_provider=mock_llm,
        tool_runner=mock_tool_runner,
    )

    # Since the tool is high risk and requires approval, execution loop breaks and transitions status to waiting_approval
    assert run.status == "waiting_approval"
    assert run.total_steps == 1  # model_call step registered, tool call blocked

    # 5. Verify ApprovalRequest was created
    stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.agent_run_id == run.id)
    res = await session.execute(stmt)
    approval_req = res.scalar_one_or_none()
    assert approval_req is not None
    assert approval_req.status == "pending"
    assert approval_req.risk_level == "high"
    assert approval_req.reviewer_role == "admin_write"
    
    # 6. Verify Context Sanitization (password and prompt redacted, safe_param preserved)
    ctx = approval_req.sanitized_context
    assert ctx["tool_name"] == "destructive_tool"
    assert ctx["tool_input"]["password"] == "<redacted>"
    assert ctx["tool_input"]["prompt"] == "<redacted>"
    assert ctx["tool_input"]["safe_param"] == "hello"

    # Verify original input is stored in raw_tool_input
    assert approval_req.raw_tool_input["password"] == "my_password_123"

    # 7. Approve request via API endpoint
    # Call the API using AdminRole.WRITE (write-token)
    headers = {"X-Admin-Token": "write-token"}
    resp = await admin_client.post(
        f"/admin/agent-approvals/{approval_req.id}/approve",
        json={"decision_reason": "Approved by security team"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["decision_reason"] == "Approved by security team"
    assert data["decided_by"] == "admin"

    # 8. Verify the run automatically resumed and finished
    await session.refresh(run)
    assert run.status == "completed"
    assert run.total_steps == 3  # model_call, tool_call, final
    assert len(tool_calls) == 1
    # Verify the tool was called with raw (unsanitized) arguments
    assert tool_calls[0][1]["password"] == "my_password_123"


@pytest.mark.asyncio
async def test_high_risk_tool_rejection_terminates_run(
    admin_client: AsyncClient, session: AsyncSession
):
    # 1. Create an active agent definition
    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "HITL Agent 2",
            "version": "1.0.0",
            "instructions": "Execute destructive tools safely.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-xyz",
            "status": "active",
            "allowed_tools": ["destructive_tool"],
            "max_steps": 10,
            "max_runtime_seconds": 300,
            "risk_level": "high",
        }
    )

    # 2. Register tool
    tool = AgentTool(
        name="destructive_tool",
        version="1.0.0",
        description="A destructive tool",
        category="filesystem_destructive",
        input_schema_json={"type": "object"},
        output_schema_json={"type": "object"},
        risk_level="high",
        side_effect_level="destructive",
        requires_approval=True,
        owner="tester",
        enabled=True,
    )
    session.add(tool)
    await session.commit()

    # 3. Setup mock responses
    llm_responses = [
        {
            "type": "tool_call",
            "tool_name": "destructive_tool",
            "tool_input": {"data": "delete_all"}
        }
    ]
    mock_llm = MockLLMProvider(responses=llm_responses)

    # 4. Start the run
    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-xyz",
        input_text="Delete resources.",
        llm_provider=mock_llm,
    )
    assert run.status == "waiting_approval"

    # Get approval request
    stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.agent_run_id == run.id)
    res = await session.execute(stmt)
    approval_req = res.scalar_one_or_none()
    assert approval_req is not None

    # 5. Reject request via API endpoint
    headers = {"X-Admin-Token": "write-token"}
    resp = await admin_client.post(
        f"/admin/agent-approvals/{approval_req.id}/reject",
        json={"decision_reason": "Dangerous operation, block"},
        headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    # 6. Verify run was marked failed
    await session.refresh(run)
    assert run.status == "failed"
    assert "rejected" in run.failure_reason


@pytest.mark.asyncio
async def test_request_changes_pauses_run(
    admin_client: AsyncClient, session: AsyncSession
):
    # 1. Create agent
    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "HITL Agent 3",
            "version": "1.0.0",
            "instructions": "Execute tools.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-xyz",
            "status": "active",
            "allowed_tools": ["destructive_tool"],
            "max_steps": 10,
            "max_runtime_seconds": 300,
            "risk_level": "high",
        }
    )

    # 2. Register tool
    tool = AgentTool(
        name="destructive_tool",
        version="1.0.0",
        description="A destructive tool",
        category="filesystem_destructive",
        input_schema_json={"type": "object"},
        output_schema_json={"type": "object"},
        risk_level="high",
        side_effect_level="destructive",
        requires_approval=True,
        owner="tester",
        enabled=True,
    )
    session.add(tool)
    await session.commit()

    mock_llm = MockLLMProvider(responses=[{
        "type": "tool_call",
        "tool_name": "destructive_tool",
        "tool_input": {"data": "delete_all"}
    }])

    # 3. Start the run
    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-xyz",
        input_text="Delete resources.",
        llm_provider=mock_llm,
    )
    assert run.status == "waiting_approval"

    # Get approval request
    stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.agent_run_id == run.id)
    res = await session.execute(stmt)
    approval_req = res.scalar_one_or_none()

    # 4. Request Changes via API endpoint
    headers = {"X-Admin-Token": "write-token"}
    resp = await admin_client.post(
        f"/admin/agent-approvals/{approval_req.id}/request-changes",
        json={"decision_reason": "Provide more details"},
        headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # 5. Verify run was marked paused
    await session.refresh(run)
    assert run.status == "paused"


@pytest.mark.asyncio
async def test_rbac_reviewer_permission_check(
    admin_client: AsyncClient, session: AsyncSession
):
    # 1. Create policy that requires super_admin
    policy = AgentApprovalPolicy(
        name="Super Admin Policy",
        trigger_type="always",
        required_role="super_admin",
        enabled=True
    )
    session.add(policy)

    agent_def = await agent_state.create_agent_definition(
        session,
        {
            "name": "HITL Agent 4",
            "version": "1.0.0",
            "instructions": "Execute tools.",
            "model_id": "mock-llm",
            "owner": "tester",
            "tenant_id": "tenant-xyz",
            "status": "active",
            "allowed_tools": ["simple_tool"],
            "max_steps": 10,
            "max_runtime_seconds": 300,
            "risk_level": "low",
        }
    )
    await session.commit()

    mock_llm = MockLLMProvider(responses=[{
        "type": "tool_call",
        "tool_name": "simple_tool",
        "tool_input": {"val": 1}
    }])

    # 2. Run triggering always-policy
    run = await agent_runtime.start_run(
        db=session,
        agent_id=agent_def.id,
        tenant_id="tenant-xyz",
        input_text="Execute always policy.",
        llm_provider=mock_llm,
    )
    assert run.status == "waiting_approval"

    stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.agent_run_id == run.id)
    res = await session.execute(stmt)
    approval_req = res.scalar_one_or_none()
    assert approval_req.reviewer_role == "super_admin"

    # 3. Call approve with READ token (read-token) -> gets 403 / 401 depending on route validation
    # Actually require_admin_role(AdminRole.READ) evaluates token: read-token has role READ.
    # When approve endpoint runs, it checks caller_role < reviewer_role.
    # since READ < SUPER, it should raise 403.
    resp = await admin_client.post(
        f"/admin/agent-approvals/{approval_req.id}/approve",
        json={"decision_reason": "Low role"},
        headers={"X-Admin-Token": "read-token"}
    )
    assert resp.status_code == 403

    # Try with WRITE token (write-token) -> WRITE < SUPER, gets 403
    resp = await admin_client.post(
        f"/admin/agent-approvals/{approval_req.id}/approve",
        json={"decision_reason": "Medium role"},
        headers={"X-Admin-Token": "write-token"}
    )
    assert resp.status_code == 403

    # Try with SUPER token (super-token) -> SUPER == SUPER, gets 200
    resp = await admin_client.post(
        f"/admin/agent-approvals/{approval_req.id}/approve",
        json={"decision_reason": "Super role ok"},
        headers={"X-Admin-Token": "super-token"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_failsafe_expiration(session: AsyncSession):
    # 1. Create a pending request
    req = AgentApprovalRequest(
        agent_run_id=uuid.uuid4(),
        risk_level="low",
        reason="Manual setup",
        requested_by="test",
        reviewer_role="admin_read",
        status="pending",
        expires_at=utc_now() - timedelta(seconds=10), # Expired 10s ago
        sanitized_context={},
        raw_tool_input={},
    )
    session.add(req)

    # Create associated run in status waiting_approval
    run = AgentRun(
        id=req.agent_run_id,
        agent_id=uuid.uuid4(),
        tenant_id="tenant-1",
        status="waiting_approval",
        input_hash="abc",
        total_steps=1,
    )
    session.add(run)
    await session.commit()

    # 2. Trigger expiration check
    await check_all_expired_requests(session)
    await session.refresh(req)
    await session.refresh(run)

    # 3. Assert expired request failsafe triggers run failure
    assert req.status == "expired"
    assert run.status == "failed"
    assert run.failure_reason == "Approval request expired"


def test_sanitize_value():
    """Verify context sanitization redacts keys and truncates long values."""
    sensitive_dict = {
        "user_prompt": "Sensitive instruction",
        "api_key": "secret_abc123",
        "normal_field": "public",
        "nested": {
            "token": "sensitive_token",
            "nested_ok": 42
        },
        "long_field": "a" * 600
    }
    sanitized = sanitize_value(sensitive_dict)

    assert sanitized["user_prompt"] == "<redacted>"
    assert sanitized["api_key"] == "<redacted>"
    assert sanitized["normal_field"] == "public"
    assert sanitized["nested"]["token"] == "<redacted>"
    assert sanitized["nested"]["nested_ok"] == 42
    assert len(sanitized["long_field"]) < 600
    assert "truncated" in sanitized["long_field"]
