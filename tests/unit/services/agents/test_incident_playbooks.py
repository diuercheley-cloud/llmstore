import uuid

import pytest
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents.agents import (
    AgentApprovalRequest,
    AgentDefinition,
    AgentIncident,
    AgentMemoryPolicy,
    AgentRun,
    AgentTool,
)
from app.models.core.admin_rbac import (
    AdminPermission,
    AdminRoleModel,
    AdminRolePermission,
    AdminUser,
    AdminUserRole,
)
from app.services.agents.agent_incident_playbooks import AgentIncidentPlaybookService
from app.services.agents.agent_memory import AgentMemoryService
from app.services.agents.agent_state import create_agent_run
from app.services.agents.incident_action_executor import IncidentActionExecutor
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def setup_rbac_user(
    session: AsyncSession, username: str, permissions: list[str]
) -> AdminUser:
    """Helper to set up an AdminUser with roles and permissions."""
    user = AdminUser(
        id=uuid.uuid4(),
        username=username,
        display_name=username,
        token_prefix=f"tok_{username}",
        token_hash="dummy_hash",
        is_active=True,
    )
    session.add(user)
    await session.flush()

    role = AdminRoleModel(
        id=uuid.uuid4(),
        name=f"role_{username}",
        description="test role",
        is_system=False,
    )
    session.add(role)
    await session.flush()

    user_role = AdminUserRole(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role.id,
    )
    session.add(user_role)
    await session.flush()

    for code in permissions:
        # Check if permission already exists
        stmt = select(AdminPermission).where(AdminPermission.code == code)
        res = await session.execute(stmt)
        perm = res.scalar_one_or_none()
        if not perm:
            perm = AdminPermission(
                id=uuid.uuid4(),
                code=code,
                description=code,
            )
            session.add(perm)
            await session.flush()

        role_perm = AdminRolePermission(
            id=uuid.uuid4(),
            role_id=role.id,
            permission_id=perm.id,
        )
        session.add(role_perm)
        await session.flush()

    await session.commit()
    return user


@pytest.mark.asyncio
async def test_disable_tool_action(session: AsyncSession):
    # Setup tool
    tool_id = uuid.uuid4()
    tool = AgentTool(
        id=tool_id,
        name="test_containment_tool",
        description="A tool to test containment actions",
        category="filesystem_safe",
        input_schema_json={},
        output_schema_json={},
        enabled=True,
    )
    session.add(tool)
    await session.commit()

    executor = IncidentActionExecutor(session)

    # 1. Dry run - should not change DB state
    report = await executor.disable_tool(
        tool_id="test_containment_tool",
        performed_by="admin_write",
        dry_run=True,
    )
    assert report["dry_run"] is True
    assert report["changed"] is False
    assert report["previous_state"] is True
    assert report["current_state"] is True

    # Refresh and check
    await session.refresh(tool)
    assert tool.enabled is True

    # 2. Real run - should disable the tool
    report = await executor.disable_tool(
        tool_id="test_containment_tool",
        performed_by="admin_write",
        dry_run=False,
    )
    assert report["dry_run"] is False
    assert report["changed"] is True
    assert report["previous_state"] is True
    assert report["current_state"] is False

    await session.refresh(tool)
    assert tool.enabled is False

    # 3. Idempotency - running again should not fail
    report2 = await executor.disable_tool(
        tool_id="test_containment_tool",
        performed_by="admin_write",
        dry_run=False,
    )
    assert report2["changed"] is False
    assert report2["current_state"] is False

    # 4. Rollback
    rollback_report = await executor.rollback(
        action_type="disable_tool",
        rollback_data=report["rollback_data"],
        performed_by="admin_write",
    )
    assert rollback_report["status"] == "success"

    await session.refresh(tool)
    assert tool.enabled is True


@pytest.mark.asyncio
async def test_quarantine_memory_action(session: AsyncSession):
    agent_id = uuid.uuid4()
    agent = AgentDefinition(
        id=agent_id,
        name="Quarantine Test Agent",
        version="1.0.0",
        description="Agent for testing memory quarantine",
        instructions="Be helpful",
        model_id="gpt-4",
        owner="test-owner",
        tenant_id="t1",
    )
    session.add(agent)

    # Add memory policy so memory write is allowed by policy engine
    retention_policy = AgentMemoryPolicy(
        tenant_id="t1",
        agent_id=agent_id,
        memory_type="short_term",
        retention_days=30,
        redaction_enabled=True,
    )
    session.add(retention_policy)
    await session.commit()

    executor = IncidentActionExecutor(session)
    mem_service = AgentMemoryService(session)

    # Set up memory globally enabled
    orig_memory_enabled = mem_service.settings.agent_memory_enabled
    orig_write_enabled = mem_service.settings.agent_memory_write_enabled
    mem_service.settings.agent_memory_enabled = True
    mem_service.settings.agent_memory_write_enabled = True

    try:
        # Write memory initially - should succeed
        item = await mem_service.write_memory(
            tenant_id="t1",
            agent_id=agent_id,
            memory_type="short_term",
            content="Hello world",
        )
        assert item is not None

        # 1. Dry run quarantine
        quarantine_report = await executor.quarantine_memory(
            target_id=str(agent_id),
            reason="Memory poisoning",
            performed_by="admin_write",
            dry_run=True,
        )
        assert quarantine_report["dry_run"] is True
        assert quarantine_report["changed"] is False

        # Verify writing still works
        item2 = await mem_service.write_memory(
            tenant_id="t1",
            agent_id=agent_id,
            memory_type="short_term",
            content="Dry run allowed",
        )
        assert item2 is not None

        # 2. Real quarantine
        quarantine_report = await executor.quarantine_memory(
            target_id=str(agent_id),
            reason="Memory poisoning",
            performed_by="admin_write",
            dry_run=False,
        )
        assert quarantine_report["dry_run"] is False
        assert quarantine_report["changed"] is True

        # Verify writing now fails
        with pytest.raises(ValueError, match="is quarantined"):
            await mem_service.write_memory(
                tenant_id="t1",
                agent_id=agent_id,
                memory_type="short_term",
                content="This should fail",
            )

        # Verify reading fails
        with pytest.raises(ValueError, match="is quarantined"):
            await mem_service.read_memory(
                tenant_id="t1",
                agent_id=agent_id,
            )

        # 3. Rollback
        await executor.rollback(
            action_type="quarantine_memory",
            rollback_data=quarantine_report["rollback_data"],
            performed_by="admin_write",
        )

        # Writing should succeed again
        item3 = await mem_service.write_memory(
            tenant_id="t1",
            agent_id=agent_id,
            memory_type="short_term",
            content="Back to normal",
        )
        assert item3 is not None

    finally:
        mem_service.settings.agent_memory_enabled = orig_memory_enabled
        mem_service.settings.agent_memory_write_enabled = orig_write_enabled


@pytest.mark.asyncio
async def test_expire_approvals_action(session: AsyncSession):
    agent_id = uuid.uuid4()
    agent = AgentDefinition(
        id=agent_id,
        name="Approval Test Agent",
        version="1.0.0",
        description="Agent for testing approvals",
        instructions="Be helpful",
        model_id="gpt-4",
        owner="test-owner",
        tenant_id="t1",
    )
    run = AgentRun(
        id=uuid.uuid4(),
        agent_id=agent_id,
        tenant_id="t1",
        status="waiting_approval",
    )
    session.add(agent)
    session.add(run)
    await session.commit()

    approval1 = AgentApprovalRequest(
        id=uuid.uuid4(),
        agent_run_id=run.id,
        risk_level="medium",
        reason="Requires tool execution permission",
        requested_by="user",
        reviewer_role="admin_write",
        status="pending",
        expires_at=utc_now(),
    )
    approval2 = AgentApprovalRequest(
        id=uuid.uuid4(),
        agent_run_id=run.id,
        risk_level="high",
        reason="Sensitive action",
        requested_by="user",
        reviewer_role="admin_write",
        status="pending",
        expires_at=utc_now(),
    )
    session.add(approval1)
    session.add(approval2)
    await session.commit()

    executor = IncidentActionExecutor(session)

    # 1. Dry run
    report = await executor.expire_approvals(
        agent_id_or_scope=str(agent_id),
        performed_by="admin_write",
        dry_run=True,
    )
    assert report["dry_run"] is True
    assert report["expired_count"] == 2
    assert report["changed"] is False

    await session.refresh(approval1)
    assert approval1.status == "pending"

    # 2. Real expire
    report = await executor.expire_approvals(
        agent_id_or_scope=str(agent_id),
        performed_by="admin_write",
        dry_run=False,
    )
    assert report["dry_run"] is False
    assert report["expired_count"] == 2
    assert report["changed"] is True

    await session.refresh(approval1)
    await session.refresh(approval2)
    assert approval1.status == "expired"
    assert approval2.status == "expired"

    # 3. Rollback
    await executor.rollback(
        action_type="expire_approvals",
        rollback_data=report["rollback_data"],
        performed_by="admin_write",
    )

    await session.refresh(approval1)
    await session.refresh(approval2)
    assert approval1.status == "pending"
    assert approval2.status == "pending"


@pytest.mark.asyncio
async def test_throttle_queue_action(session: AsyncSession):
    agent_id = uuid.uuid4()
    agent = AgentDefinition(
        id=agent_id,
        name="Queue Test Agent",
        version="1.0.0",
        description="Agent for testing queue throttle",
        instructions="Be helpful",
        model_id="gpt-4",
        owner="test-owner",
        tenant_id="t1",
    )
    session.add(agent)
    await session.commit()

    # Pre-create a queued run
    await create_agent_run(
        db=session,
        agent_id=agent_id,
        tenant_id="t1",
        input_text="First run",
    )

    executor = IncidentActionExecutor(session)

    # 1. Dry run throttle
    throttle_report = await executor.throttle_queue(
        target_id=str(agent_id),
        limit=1,
        performed_by="admin_write",
        dry_run=True,
    )
    assert throttle_report["dry_run"] is True
    assert throttle_report["limit"] == 1
    assert throttle_report["changed"] is False

    # Dry run should not block new runs
    run2 = await create_agent_run(
        db=session,
        agent_id=agent_id,
        tenant_id="t1",
        input_text="Second run during dry run",
    )
    assert run2 is not None

    # Change status of run2 to completed so we only have 1 active queued run
    run2.status = "completed"
    session.add(run2)
    await session.commit()

    # 2. Real throttle
    throttle_report = await executor.throttle_queue(
        target_id=str(agent_id),
        limit=1,
        performed_by="admin_write",
        dry_run=False,
    )
    assert throttle_report["dry_run"] is False
    assert throttle_report["limit"] == 1
    assert throttle_report["changed"] is True

    # Try creating a new run - should fail since we already have 1 queued run
    with pytest.raises(ValueError, match="limit of 1 queued runs"):
        await create_agent_run(
            db=session,
            agent_id=agent_id,
            tenant_id="t1",
            input_text="This should fail",
        )

    # 3. Rollback
    await executor.rollback(
        action_type="throttle_queue",
        rollback_data=throttle_report["rollback_data"],
        performed_by="admin_write",
    )

    # Try creating new run again - should work now
    run3 = await create_agent_run(
        db=session,
        agent_id=agent_id,
        tenant_id="t1",
        input_text="This should now succeed",
    )
    assert run3 is not None


@pytest.mark.asyncio
async def test_rbac_permissions_validation(session: AsyncSession):
    # Enable RBAC settings dynamically for this test
    settings = get_settings()
    orig_rbac_enabled = settings.rbac_admin_enabled
    settings.rbac_admin_enabled = True

    try:
        # Create user with governance:write
        await setup_rbac_user(session, "gov_user", ["governance:write"])
        # Create user with no governance permissions
        await setup_rbac_user(session, "non_gov_user", ["clients:read"])

        # Setup tool
        tool = AgentTool(
            id=uuid.uuid4(),
            name="rbac_test_tool",
            category="filesystem_safe",
            input_schema_json={},
            output_schema_json={},
            enabled=True,
        )
        session.add(tool)
        await session.commit()

        executor = IncidentActionExecutor(session)

        # Attempt disable_tool with unauthorized user - should raise ValueError
        with pytest.raises(
            ValueError, match="does not have required 'governance:write' permission"
        ):
            await executor.disable_tool(
                tool_id="rbac_test_tool",
                performed_by="non_gov_user",
                dry_run=False,
            )

        # Attempt with authorized user - should succeed
        report = await executor.disable_tool(
            tool_id="rbac_test_tool",
            performed_by="gov_user",
            dry_run=False,
        )
        assert report["changed"] is True

    finally:
        settings.rbac_admin_enabled = orig_rbac_enabled


@pytest.mark.asyncio
async def test_playbook_service_integration(session: AsyncSession):
    # Setup tool
    tool = AgentTool(
        id=uuid.uuid4(),
        name="playbook_test_tool",
        category="filesystem_safe",
        input_schema_json={},
        output_schema_json={},
        enabled=True,
    )
    agent_id = uuid.uuid4()
    agent = AgentDefinition(
        id=agent_id,
        name="Playbook Test Agent",
        version="1.0.0",
        description="Agent for testing playbook service",
        instructions="Be helpful",
        model_id="gpt-4",
        owner="test-owner",
        tenant_id="t1",
    )
    incident = AgentIncident(
        id=uuid.uuid4(),
        tenant_id="t1",
        agent_id=agent_id,
        incident_type="tool_cascade_failure",
        status="open",
        title="Tool Cascade Failure",
        details_json={"tool_name": "playbook_test_tool"},
    )
    session.add(tool)
    session.add(agent)
    session.add(incident)
    await session.commit()

    playbook_service = AgentIncidentPlaybookService(session)

    # Run tool-cascade-failure playbook
    report = await playbook_service.execute_playbook(
        incident_id=incident.id,
        playbook_id="tool-cascade-failure",
        performed_by="admin_write",
        confirmation=True,
    )

    assert incident.status == "resolved"
    assert len(report["actions"]) == 1
    assert report["actions"][0]["action"] == "disable_tool"
    assert report["actions"][0]["changed"] is True

    await session.refresh(tool)
    assert tool.enabled is False
