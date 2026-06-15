# Owner: agent-platform
import uuid

from app.models.agents.agents import AgentA2ARegistration, AgentDefinition
from app.services.agents.a2a.a2a_security import A2ASecurityService
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class A2ARegistryService:
    @staticmethod
    async def register_agent(
        db: AsyncSession,
        tenant_id: str,
        agent_id: uuid.UUID,
        auth_token: str,
        target_url: str | None = None,
        capabilities: dict | None = None,
        is_external: bool = False,
        agent_name: str | None = None,
    ) -> AgentA2ARegistration:
        A2ASecurityService.verify_a2a_enabled_or_raise()
        if is_external:
            A2ASecurityService.verify_external_enabled_or_raise()

        # Check if agent definition exists, if not and external, create one
        stmt_def = select(AgentDefinition).where(AgentDefinition.id == agent_id)
        res_def = await db.execute(stmt_def)
        agent_def = res_def.scalar_one_or_none()

        if not agent_def:
            if is_external:
                # Create a placeholder AgentDefinition for this external agent
                agent_def = AgentDefinition(
                    id=agent_id,
                    name=agent_name or f"External A2A Agent {agent_id}",
                    version="1.0.0",
                    instructions="External A2A delegated actions",
                    model_id="external",
                    owner="external",
                    tenant_id=tenant_id,
                    status="active",
                    allowed_tools=["*"],
                )
                db.add(agent_def)
                await db.flush()
            else:
                raise HTTPException(
                    status_code=404, detail=f"Agent definition {agent_id} not found."
                )
        else:
            # Tenant check for internal agent
            if agent_def.tenant_id != tenant_id:
                raise HTTPException(status_code=403, detail="Cross-tenant registration is blocked.")

        # Upsert registration
        stmt_reg = select(AgentA2ARegistration).where(AgentA2ARegistration.agent_id == agent_id)
        res_reg = await db.execute(stmt_reg)
        reg = res_reg.scalar_one_or_none()

        if reg:
            # Tenant check for safety on updates
            if reg.tenant_id != tenant_id:
                raise HTTPException(status_code=403, detail="Cross-tenant update is blocked.")
            reg.target_url = target_url
            reg.auth_token = auth_token
            reg.capabilities = capabilities or {}
            reg.is_external = is_external
        else:
            reg = AgentA2ARegistration(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                agent_id=agent_id,
                target_url=target_url,
                auth_token=auth_token,
                capabilities=capabilities or {},
                is_external=is_external,
            )
            db.add(reg)

        await db.commit()
        await db.refresh(reg)
        return reg

    @staticmethod
    async def list_registered_agents(
        db: AsyncSession, tenant_id: str
    ) -> list[AgentA2ARegistration]:
        A2ASecurityService.verify_a2a_enabled_or_raise()
        stmt = select(AgentA2ARegistration).where(AgentA2ARegistration.tenant_id == tenant_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_agent_registration(
        db: AsyncSession, agent_id: uuid.UUID, tenant_id: str
    ) -> AgentA2ARegistration | None:
        A2ASecurityService.verify_a2a_enabled_or_raise()
        stmt = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == agent_id, AgentA2ARegistration.tenant_id == tenant_id
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
