import asyncio
import importlib
import uuid
from datetime import timedelta
from pathlib import Path

import app.db.session
import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.base import Base
from app.models.agents.agent_tool_execution import (
    AgentToolExecutionAudit,
    AgentToolExecutionSandbox,
    AgentToolQuotaCounter,
    AgentToolRollbackAction,
    AgentToolSideEffect,
)
from app.models.agents.agents import (
    AgentApprovalRequest,
    AgentRegistryEntry,
    AgentTool,
    AgentToolInvocation,
)
from app.services.agents.tool_credentials import (
    grant_credential,
    register_credential,
    resolve_credential,
    revoke_credential,
)
from app.services.agents.tool_executor import execute_tool
from app.services.agents.tool_quota import QuotaExceededError
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    db_file = Path(f"/tmp/test-agent-tool-exec-{uuid.uuid4()}.db")
    db_url = f"sqlite+aiosqlite:///{db_file}"
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    orig_engine = app.db.session.engine
    orig_session = app.db.session.SessionLocal
    app.db.session.engine = engine
    app.db.session.SessionLocal = session_factory

    async with engine.begin() as conn:
        importlib.import_module("app.models.agents.agents")
        importlib.import_module("app.models.agents.agent_tool_execution")
        await conn.run_sync(Base.metadata.create_all)

    yield session_factory

    await engine.dispose()
    if db_file.exists():
        db_file.unlink()

    app.db.session.engine = orig_engine
    app.db.session.SessionLocal = orig_session


@pytest.fixture
def run_settings():
    settings = get_settings()
    # Save original values
    orig_execution = settings.agent_tool_execution_enabled
    orig_sandbox = settings.agent_tool_sandbox_enabled
    orig_destructive = settings.agent_destructive_tools_enabled
    orig_delegation = settings.agent_tool_credential_delegation_enabled
    orig_rollback = settings.agent_tool_rollback_enabled
    orig_registry = settings.agent_tool_registry_enabled
    orig_key = settings.commercial_tenant_encryption_master_key

    # Set sensible test defaults
    settings.agent_tool_registry_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_tool_sandbox_enabled = True
    settings.agent_destructive_tools_enabled = False
    settings.agent_tool_credential_delegation_enabled = True
    settings.agent_tool_rollback_enabled = True
    settings.commercial_tenant_encryption_master_key = "test-master-key-must-be-32-bytes-long-12345"

    yield settings

    # Restore original values
    settings.agent_tool_execution_enabled = orig_execution
    settings.agent_tool_sandbox_enabled = orig_sandbox
    settings.agent_destructive_tools_enabled = orig_destructive
    settings.agent_tool_credential_delegation_enabled = orig_delegation
    settings.agent_tool_rollback_enabled = orig_rollback
    settings.agent_tool_registry_enabled = orig_registry
    settings.commercial_tenant_encryption_master_key = orig_key


async def create_mock_tool(
    db: AsyncSession,
    name: str = "test_tool",
    category: str = "filesystem_safe",
    side_effect_level: str = "none",
    requires_approval: bool = False,
    dry_run_supported: bool = True,
    rollback_supported: bool = True,
    timeout_seconds: int = 5,
) -> AgentTool:
    tool = AgentTool(
        id=uuid.uuid4(),
        name=name,
        version="0.1.0",
        description="A mock tool for testing",
        category=category,
        input_schema_json={"type": "object", "properties": {"param1": {"type": "string"}}},
        output_schema_json={"type": "object", "properties": {"result": {"type": "string"}}},
        risk_level="low",
        side_effect_level=side_effect_level,
        timeout_seconds=timeout_seconds,
        enabled=True,
        requires_approval=requires_approval,
        dry_run_supported=dry_run_supported,
        rollback_supported=rollback_supported,
    )
    db.add(tool)
    await db.commit()
    return tool


async def create_mock_agent(
    db: AsyncSession, surface_status: str = "internal"
) -> AgentRegistryEntry:
    agent = AgentRegistryEntry(
        id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        name="Test Agent",
        semantic_version="0.1.0",
        owner="tester",
        supported_surface_status=surface_status,
        risk_level="low",
        approval_required=False,
        status="active",
    )
    db.add(agent)
    await db.commit()
    return agent


@pytest.mark.asyncio
async def test_disabled_tool_execution_flag_blocks_execution(run_settings):
    run_settings.agent_tool_execution_enabled = False

    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "test_tool")

        with pytest.raises(ValueError, match="Tool execution is disabled by feature flag"):
            await execute_tool(db=db, tool=tool, parameters={"param1": "val"}, tenant_id="tenant-1")


@pytest.mark.asyncio
async def test_sandbox_mock_execution(run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "test_tool")

        output = await execute_tool(
            db=db, tool=tool, parameters={"param1": "hello"}, tenant_id="tenant-1"
        )

        assert output["status"] == "success"
        assert "Sandbox execution mock" in output["message"]

        # Verify sandbox log in DB
        stmt = select(AgentToolExecutionSandbox).where(
            AgentToolExecutionSandbox.tenant_id == "tenant-1"
        )
        res = await db.execute(stmt)
        sandbox = res.scalar_one()
        assert sandbox.status == "success"
        assert not sandbox.output_truncated
        assert "mock output" in sandbox.output_log


@pytest.mark.asyncio
async def test_sandbox_runtime_timeout(run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "slow_tool", timeout_seconds=1)

        async def slow_callable(**kwargs):
            await asyncio.sleep(2)
            return {"result": "done"}

        with pytest.raises(asyncio.TimeoutError):
            await execute_tool(
                db=db,
                tool=tool,
                parameters={"param1": "hello"},
                tool_callable=slow_callable,
                tenant_id="tenant-1",
            )

        # Verify sandbox record
        stmt = select(AgentToolExecutionSandbox).where(
            AgentToolExecutionSandbox.tenant_id == "tenant-1"
        )
        res = await db.execute(stmt)
        sandbox = res.scalar_one()
        assert sandbox.status == "timeout"


@pytest.mark.asyncio
async def test_sandbox_output_truncation(run_settings):
    async with app.db.session.SessionLocal() as db:
        # We need a small output limit. We pass output_limit_bytes to the test by wrapping/mocking, or we can use tool execution sandbox helper directly or mock size.
        # Let's customize execute_in_sandbox call in executor, or we can just call execute_in_sandbox directly to verify truncation logic.
        from app.services.agents.tool_sandbox import execute_in_sandbox

        invocation_id = uuid.uuid4()

        async def large_callable(**kwargs):
            return {"data": "A" * 100}

        output = await execute_in_sandbox(
            db=db,
            tenant_id="tenant-1",
            invocation_id=invocation_id,
            tool_name="large_tool",
            tool_category="filesystem_safe",
            parameters={},
            allowed_commands=["*"],
            timeout_seconds=5,
            output_limit_bytes=20,
            tool_callable=large_callable,
        )

        assert output["status"] == "truncated"
        assert output["message"] == "Output exceeded size limit and was truncated."

        # Verify sandbox record in DB
        stmt = select(AgentToolExecutionSandbox).where(
            AgentToolExecutionSandbox.invocation_id == invocation_id
        )
        res = await db.execute(stmt)
        sandbox = res.scalar_one()
        assert sandbox.output_truncated is True
        assert "[TRUNCATED]" in sandbox.output_log


@pytest.mark.asyncio
async def test_shell_command_blocking_default(run_settings):
    run_settings.agent_destructive_tools_enabled = False

    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "shell_tool", category="shell_command")

        with pytest.raises(ValueError, match="Shell commands are disabled by default"):
            await execute_tool(db=db, tool=tool, parameters={"command": "ls"}, tenant_id="tenant-1")


@pytest.mark.asyncio
async def test_destructive_tools_flag_blocks(run_settings):
    run_settings.agent_destructive_tools_enabled = False

    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "format_drive", side_effect_level="destructive")

        with pytest.raises(
            ValueError, match="Destructive tool execution is disabled by feature flag"
        ):
            await execute_tool(db=db, tool=tool, parameters={"param1": "foo"}, tenant_id="tenant-1")


@pytest.mark.asyncio
async def test_human_approval_requirement(run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(
            db, "write_tool", side_effect_level="write", requires_approval=True
        )

        # 1. Blocks execution without approval
        with pytest.raises(ValueError, match="Tool execution requires human approval"):
            await execute_tool(
                db=db,
                tool=tool,
                parameters={"param1": "data"},
                run_id=uuid.uuid4(),
                tenant_id="tenant-1",
            )

        # 2. Succeeds when executed by admin
        output_admin = await execute_tool(
            db=db,
            tool=tool,
            parameters={"param1": "data"},
            tenant_id="tenant-1",
            executed_by="admin",
        )
        assert output_admin["status"] == "success"

        # 3. Succeeds when approved
        run_id = uuid.uuid4()
        approval = AgentApprovalRequest(
            id=uuid.uuid4(),
            agent_run_id=run_id,
            status="approved",
            expires_at=utc_now() + timedelta(hours=1),
            reason="Approved by user",
            requested_by="agent",
            sanitized_context={"tool_name": tool.name},
        )
        db.add(approval)
        await db.commit()

        output_approved = await execute_tool(
            db=db,
            tool=tool,
            parameters={"param1": "data"},
            run_id=run_id,
            tenant_id="tenant-1",
            executed_by="agent",
        )
        assert output_approved["status"] == "success"


@pytest.mark.asyncio
async def test_credential_delegation_resolution(run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "cred_tool")

        # Register a credential
        cred = await register_credential(
            db=db,
            tenant_id="tenant-1",
            name="API Key",
            credential_type="api_key",
            raw_secret="super-secret-key-12345",
        )

        # Grant to tool
        await grant_credential(
            db=db, tenant_id="tenant-1", credential_id=cred.id, agent_tool_id=tool.id
        )
        await db.commit()

        # Resolve and check it decryption
        secret = await resolve_credential(db, "tenant-1", tool.id)
        assert secret == "super-secret-key-12345"

        # Check masking format
        assert cred.secret_masked == "sup...345"

        # Execute tool and verify parameter injection
        output = await execute_tool(
            db=db, tool=tool, parameters={"param1": "val"}, tenant_id="tenant-1"
        )
        assert output["status"] == "success"

        # Verify secret is not logged raw in audits
        stmt = select(AgentToolExecutionAudit).where(
            AgentToolExecutionAudit.tenant_id == "tenant-1"
        )
        res = await db.execute(stmt)
        audits = res.scalars().all()

        for audit in audits:
            details_str = str(audit.details)
            assert "super-secret-key-12345" not in details_str
            if "api_key" in details_str or "secret" in details_str:
                assert "[REDACTED]" in details_str


@pytest.mark.asyncio
async def test_revoked_credential_blocks(run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "secret_tool")

        cred = await register_credential(
            db=db,
            tenant_id="tenant-1",
            name="API Key",
            credential_type="api_key",
            raw_secret="secret-key",
        )

        await grant_credential(
            db=db, tenant_id="tenant-1", credential_id=cred.id, agent_tool_id=tool.id
        )
        await db.commit()

        # Revoke
        success = await revoke_credential(db, "tenant-1", cred.id)
        assert success is True
        await db.commit()

        # Resolve should return None
        secret = await resolve_credential(db, "tenant-1", tool.id)
        assert secret is None


@pytest.mark.asyncio
async def test_expired_credential_blocks(run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "secret_tool")

        cred = await register_credential(
            db=db,
            tenant_id="tenant-1",
            name="API Key",
            credential_type="api_key",
            raw_secret="secret-key",
            expires_at=utc_now() - timedelta(seconds=1),
        )

        await grant_credential(
            db=db, tenant_id="tenant-1", credential_id=cred.id, agent_tool_id=tool.id
        )
        await db.commit()

        secret = await resolve_credential(db, "tenant-1", tool.id)
        assert secret is None


@pytest.mark.asyncio
async def test_quota_limits(run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "test_tool")

        # We can update the limit of a counter manually in the DB to test
        # Let's invoke once, which will create the counter.
        await execute_tool(db=db, tool=tool, parameters={"param1": "val"}, tenant_id="tenant-1")

        # Fetch the counter and change its max_limit to 1
        stmt = select(AgentToolQuotaCounter).where(AgentToolQuotaCounter.tenant_id == "tenant-1")
        res = await db.execute(stmt)
        counter = res.scalars().first()
        assert counter is not None
        counter.max_limit = 1
        await db.commit()

        # Next execution should raise QuotaExceededError
        with pytest.raises(QuotaExceededError, match="Quota exceeded"):
            await execute_tool(db=db, tool=tool, parameters={"param1": "val"}, tenant_id="tenant-1")


@pytest.mark.asyncio
async def test_dry_run_no_side_effects(run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "write_tool", side_effect_level="write")

        output = await execute_tool(
            db=db, tool=tool, parameters={"param1": "val"}, tenant_id="tenant-1", is_dry_run=True
        )

        assert output["status"] == "dry_run_success"

        # Verify no side effect or rollback registered
        stmt_se = select(AgentToolSideEffect)
        res_se = await db.execute(stmt_se)
        assert len(res_se.scalars().all()) == 0


@pytest.mark.asyncio
async def test_rollback_execution(run_settings):
    rollback_called = False
    rollback_params = {}

    def compensation_fn(**kwargs):
        nonlocal rollback_called, rollback_params
        rollback_called = True
        rollback_params = kwargs

    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(
            db=db,
            name="write_tool",
            category="filesystem_safe",
            side_effect_level="write",
            rollback_supported=True,
        )

        # Call with a tool_callable that raises exception to trigger auto rollback
        async def failing_tool(**kwargs):
            raise RuntimeError("Operation failed mid-way")

        with pytest.raises(RuntimeError):
            await execute_tool(
                db=db,
                tool=tool,
                parameters={"resource_id": "res-123", "param1": "value"},
                tool_callable=failing_tool,
                rollback_callable=compensation_fn,
                tenant_id="tenant-1",
            )

        # Verify compensation was called
        assert rollback_called is True
        assert rollback_params == {"resource_id": "res-123"}

        # Verify status of invocation is rolled_back
        stmt = select(AgentToolInvocation).where(AgentToolInvocation.status == "rolled_back")
        res = await db.execute(stmt)
        inv = res.scalars().first()
        assert inv is not None

        # Verify status of rollback action in DB is success
        stmt_ra = select(AgentToolRollbackAction)
        res_ra = await db.execute(stmt_ra)
        action = res_ra.scalars().first()
        assert action.status == "success"


@pytest.mark.asyncio
async def test_api_endpoints(async_client, admin_token_headers, run_settings):
    async with app.db.session.SessionLocal() as db:
        tool = await create_mock_tool(db, "api_tool", side_effect_level="write")
        tool_id = tool.id

    # 1. POST dry-run
    response = await async_client.post(
        f"/admin/agent-tools/{tool_id}/dry-run",
        json={"parameters": {"param1": "test"}},
        headers=admin_token_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "dry_run_success"

    # 2. POST execute (real execution)
    response = await async_client.post(
        f"/admin/agent-tools/{tool_id}/execute",
        json={"parameters": {"param1": "test"}},
        headers=admin_token_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "success"

    # 3. GET side-effects
    response = await async_client.get(
        "/admin/agent-tools/side-effects", headers=admin_token_headers
    )
    assert response.status_code == status.HTTP_200_OK
    effects = response.json()
    assert len(effects) > 0
    assert effects[0]["side_effect_level"] == "write"

    # 4. POST credentials
    response = await async_client.post(
        "/admin/agent-tools/credentials",
        json={
            "name": "API Key",
            "credential_type": "api_key",
            "raw_secret": "my-secret-key-999",
            "tenant_id": "default",
            "agent_tool_id": str(tool_id),
        },
        headers=admin_token_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    cred_id = response.json()["id"]
    assert response.json()["secret_masked"] == "my-...999"

    # 5. GET credentials
    response = await async_client.get("/admin/agent-tools/credentials", headers=admin_token_headers)
    assert response.status_code == status.HTTP_200_OK
    creds = response.json()
    assert len(creds) > 0
    # No secret values exposed
    for cred in creds:
        assert "my-secret-key-999" not in str(cred)

    # 6. POST revoke credential
    response = await async_client.post(
        f"/admin/agent-tools/credentials/{cred_id}/revoke", headers=admin_token_headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True

    # 7. GET quotas
    response = await async_client.get("/admin/agent-tools/quotas", headers=admin_token_headers)
    assert response.status_code == status.HTTP_200_OK
    quotas = response.json()
    assert len(quotas) > 0
