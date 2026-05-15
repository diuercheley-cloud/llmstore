import pytest
import uuid
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.inference import agent_governance
from app.models.commercial_agents import CommercialAgentProfile, CommercialAgentExecution

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base

@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_local() as s:
        yield s
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_agent_profile(session: AsyncSession):
    profile = await agent_governance.create_agent_profile(
        session, "Researcher", allowed_tools=["search", "browser"]
    )
    assert profile.agent_name == "Researcher"
    assert "search" in profile.allowed_tools

@pytest.mark.asyncio
async def test_agent_execution_tracking(session: AsyncSession):
    profile = await agent_governance.create_agent_profile(session, "Worker")
    
    execution = await agent_governance.start_agent_execution(
        session, profile.id, "session-123", "Run analysis"
    )
    assert execution.session_id == "session-123"
    assert execution.status == "running"

@pytest.mark.asyncio
async def test_tool_authorization_allowed(session: AsyncSession):
    profile = await agent_governance.create_agent_profile(
        session, "ToolUser", allowed_tools=["calculator"], can_delegate=False
    )
    execution = await agent_governance.start_agent_execution(session, profile.id, "s1", "calc")
    
    # We need to ensure requires_approval_for_tools is false for auto-approval test
    profile.requires_approval_for_tools = False
    await session.commit()
    
    allowed, msg = await agent_governance.authorize_tool_execution(
        session, execution.id, "calculator", {"expression": "2+2"}
    )
    assert allowed == True
    assert msg == "Authorized"

@pytest.mark.asyncio
async def test_tool_authorization_blocked(session: AsyncSession):
    profile = await agent_governance.create_agent_profile(
        session, "Restricted", allowed_tools=["safe_tool"]
    )
    execution = await agent_governance.start_agent_execution(session, profile.id, "s1", "hack")
    
    allowed, msg = await agent_governance.authorize_tool_execution(
        session, execution.id, "dangerous_tool", {}
    )
    assert allowed == False
    assert "not in agent's allow-list" in msg

@pytest.mark.asyncio
async def test_delegation_check(session: AsyncSession):
    a1 = await agent_governance.create_agent_profile(session, "Manager", can_delegate=True)
    a2 = await agent_governance.create_agent_profile(session, "Worker")
    
    allowed = await agent_governance.check_delegation_allowed(session, a1.id, a2.id)
    assert allowed == True # Fallback to global can_delegate
