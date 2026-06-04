import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents import AgentRBACEvent
from app.services.admin_rbac import AdminUser, AuthenticatedAdmin
from app.services.agents.agent_environment_policy import AgentEnvironmentPolicyService
from app.services.agents.agent_rbac import check_agent_permission
from app.services.agents.ephemeral_credentials import EphemeralCredentialService
from fastapi import HTTPException


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents  # noqa
        import app.models.admin_rbac # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

def _mock_admin(permissions: list[str]) -> AuthenticatedAdmin:
    user = AdminUser(id=uuid.uuid4(), username="test-user")
    return AuthenticatedAdmin(
        user=user,
        role_names=["test-role"],
        permission_codes=set(permissions),
        token_prefix="test"
    )

@pytest.mark.asyncio
async def test_viewer_cannot_execute_agent():
    async with SessionLocal() as db:
        admin = _mock_admin(["agents:read"])
        
        # Should raise 403
        with pytest.raises(HTTPException) as exc:
            await check_agent_permission(db, admin, "agents:execute")
        assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_developer_cannot_approve_destructive_tool():
    # In this mock, we just check if they have the specific permission
    async with SessionLocal() as db:
        admin = _mock_admin(["agents:write", "agents:execute"])
        
        with pytest.raises(HTTPException):
            await check_agent_permission(db, admin, "agents:approve")

@pytest.mark.asyncio
async def test_sovereign_blocks_external_tool():
    async with SessionLocal() as db:
        svc = AgentEnvironmentPolicyService(db)
        agent_id = uuid.uuid4()
        
        # Blocks by default in sovereign
        allowed = await svc.check_tool_access(agent_id, "external_search", "sovereign")
        assert allowed is False

@pytest.mark.asyncio
async def test_sovereign_allows_external_tool_with_exception():
    async with SessionLocal() as db:
        svc = AgentEnvironmentPolicyService(db)
        agent_id = uuid.uuid4()
        
        # Create exception
        await svc.create_exception(agent_id, "sovereign_tool_block", "Needed for research", "admin")
        
        allowed = await svc.check_tool_access(agent_id, "external_search", "sovereign")
        assert allowed is True

@pytest.mark.asyncio
async def test_expired_credential_fails():
    async with SessionLocal() as db:
        svc = EphemeralCredentialService(db)
        run_id = uuid.uuid4()
        
        # Issue expired credential
        from app.core.time import utc_now
        from app.models.agents import AgentEphemeralCredential
        cred = AgentEphemeralCredential(
            run_id=run_id,
            scope="tool_a",
            credential_type="bearer",
            credential_value="secret",
            expires_at=utc_now() - timedelta(minutes=1),
            created_at=utc_now() - timedelta(minutes=10)
        )
        db.add(cred)
        await db.commit()
        
        val = await svc.get_valid_credential(run_id, "tool_a")
        assert val is None

@pytest.mark.asyncio
async def test_denied_permission_generates_audit_event():
    async with SessionLocal() as db:
        admin = _mock_admin(["agents:read"])
        
        try:
            await check_agent_permission(db, admin, "agents:execute")
        except HTTPException:
            pass
            
        from sqlalchemy import select
        res = await db.execute(select(AgentRBACEvent).where(AgentRBACEvent.admin_user_id == admin.user.id))
        event = res.scalar_one()
        assert event.permission_code == "agents:execute"
        assert event.status == "denied"
