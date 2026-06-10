import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.agents.agents import AgentA2ARegistration, AgentDefinition
from app.services.agents.a2a.a2a_registry import A2ARegistryService
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def patch_a2a_enabled():
    with patch("app.services.agents.a2a.a2a_security.A2ASecurityService.verify_a2a_enabled_or_raise"):
        with patch("app.services.agents.a2a.a2a_security.A2ASecurityService.verify_external_enabled_or_raise"):
            yield


class TestA2ARegistryService:
    @pytest.mark.asyncio
    async def test_register_internal_agent(self):
        agent_id = uuid.uuid4()
        agent_def = AgentDefinition(id=agent_id, tenant_id="tenant-1", name="Test Agent")

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: agent_def),
            MagicMock(scalar_one_or_none=lambda: None),
        ])

        reg = await A2ARegistryService.register_agent(
            db=db, tenant_id="tenant-1", agent_id=agent_id,
            auth_token="token-123", target_url=None,
            capabilities={"tools": ["search"]}, is_external=False,
        )
        assert reg.tenant_id == "tenant-1"
        assert reg.agent_id == agent_id
        assert reg.auth_token == "token-123"
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_external_agent_creates_definition(self):
        agent_id = uuid.uuid4()

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: None),
            MagicMock(scalar_one_or_none=lambda: None),
        ])

        reg = await A2ARegistryService.register_agent(
            db=db, tenant_id="tenant-1", agent_id=agent_id,
            auth_token="ext-token", target_url="https://ext.example.com/a2a",
            capabilities={}, is_external=True, agent_name="External Agent",
        )
        assert reg.is_external is True
        assert reg.target_url == "https://ext.example.com/a2a"
        assert db.add.call_count >= 1

    @pytest.mark.asyncio
    async def test_register_internal_missing_definition_raises(self):
        agent_id = uuid.uuid4()

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        with pytest.raises(HTTPException) as exc:
            await A2ARegistryService.register_agent(
                db=db, tenant_id="tenant-1", agent_id=agent_id,
                auth_token="token", is_external=False,
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_register_cross_tenant_raises(self):
        agent_id = uuid.uuid4()
        agent_def = AgentDefinition(id=agent_id, tenant_id="other-tenant", name="Other")

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: agent_def),
        ])

        with pytest.raises(HTTPException) as exc:
            await A2ARegistryService.register_agent(
                db=db, tenant_id="tenant-1", agent_id=agent_id,
                auth_token="token", is_external=False,
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_upsert_existing_registration(self):
        agent_id = uuid.uuid4()
        agent_def = AgentDefinition(id=agent_id, tenant_id="tenant-1", name="Test")
        existing_reg = AgentA2ARegistration(
            id=uuid.uuid4(), tenant_id="tenant-1", agent_id=agent_id,
            auth_token="old-token",
        )

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=lambda: agent_def),
            MagicMock(scalar_one_or_none=lambda: existing_reg),
        ])

        reg = await A2ARegistryService.register_agent(
            db=db, tenant_id="tenant-1", agent_id=agent_id,
            auth_token="new-token", target_url="https://new.url",
        )
        assert reg.auth_token == "new-token"
        assert reg.target_url == "https://new.url"
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_list_registered_agents(self):
        agent_id = uuid.uuid4()
        reg = AgentA2ARegistration(
            id=uuid.uuid4(), tenant_id="tenant-1", agent_id=agent_id, auth_token="token",
        )

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: [reg])
        ))

        agents = await A2ARegistryService.list_registered_agents(db, "tenant-1")
        assert len(agents) == 1
        assert agents[0].tenant_id == "tenant-1"

    @pytest.mark.asyncio
    async def test_list_registered_agents_empty(self):
        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(return_value=MagicMock(
            scalars=lambda: MagicMock(all=lambda: [])
        ))

        agents = await A2ARegistryService.list_registered_agents(db, "tenant-1")
        assert agents == []

    @pytest.mark.asyncio
    async def test_get_agent_registration_found(self):
        agent_id = uuid.uuid4()
        reg = AgentA2ARegistration(
            id=uuid.uuid4(), tenant_id="tenant-1", agent_id=agent_id, auth_token="token",
        )

        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: reg))

        result = await A2ARegistryService.get_agent_registration(db, agent_id, "tenant-1")
        assert result is not None
        assert result.agent_id == agent_id

    @pytest.mark.asyncio
    async def test_get_agent_registration_not_found(self):
        db = MagicMock(spec=AsyncSession)
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

        result = await A2ARegistryService.get_agent_registration(db, uuid.uuid4(), "tenant-1")
        assert result is None
