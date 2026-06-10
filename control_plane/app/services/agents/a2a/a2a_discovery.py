import logging
import uuid
from typing import Any, Dict, Optional

from app.models.agents.agents import AgentA2ARegistration, AgentDefinition
from app.services.agents.a2a.a2a_security import A2ASecurityService
from fastapi import HTTPException
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class A2ADiscoveryService:
    """
    Dynamic agent discovery for A2A protocol.
    Enables agents to discover each other by capabilities, tools, or name.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def discover_agents(
        self,
        tenant_id: str,
        capability: Optional[str] = None,
        tool_name: Optional[str] = None,
        name_query: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        A2ASecurityService.verify_a2a_enabled_or_raise()

        stmt = select(AgentA2ARegistration).where(
            AgentA2ARegistration.tenant_id == tenant_id
        )

        if capability:
            stmt = stmt.where(
                AgentA2ARegistration.capabilities[capability].as_string().isnot(None)
            )

        # Count total
        count_stmt = select(sa_func.count()).select_from(stmt.subquery())
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        registrations = list(res.scalars().all())

        results = []
        for reg in registrations:
            agent_def = await self.db.get(AgentDefinition, reg.agent_id)
            agent_name = agent_def.name if agent_def else "Unknown"

            # In-memory filter for tool_name
            if tool_name:
                caps = reg.capabilities or {}
                tools = caps.get("tools", [])
                if tool_name not in tools:
                    continue

            # In-memory filter for name_query
            if name_query and name_query.lower() not in agent_name.lower():
                continue

            results.append({
                "agent_id": str(reg.agent_id),
                "agent_name": agent_name,
                "target_url": reg.target_url,
                "capabilities": reg.capabilities or {},
                "is_external": reg.is_external,
                "registered_at": reg.created_at.isoformat() if reg.created_at else None,
            })

        return {
            "agents": results,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_agent_profile(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        A2ASecurityService.verify_a2a_enabled_or_raise()

        stmt = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == agent_id,
            AgentA2ARegistration.tenant_id == tenant_id,
        )
        res = await self.db.execute(stmt)
        reg = res.scalar_one_or_none()
        if not reg:
            return None

        agent_def = await self.db.get(AgentDefinition, agent_id)
        return {
            "agent_id": str(reg.agent_id),
            "agent_name": agent_def.name if agent_def else "Unknown",
            "target_url": reg.target_url,
            "capabilities": reg.capabilities or {},
            "is_external": reg.is_external,
            "registered_at": reg.created_at.isoformat() if reg.created_at else None,
        }

    async def announce_presence(
        self,
        tenant_id: str,
        agent_id: uuid.UUID,
        capabilities: Dict[str, Any],
    ) -> dict:
        A2ASecurityService.verify_a2a_enabled_or_raise()

        stmt = select(AgentA2ARegistration).where(
            AgentA2ARegistration.agent_id == agent_id,
            AgentA2ARegistration.tenant_id == tenant_id,
        )
        res = await self.db.execute(stmt)
        reg = res.scalar_one_or_none()

        if not reg:
            raise HTTPException(status_code=404, detail="Agent not registered for A2A")

        reg.capabilities = capabilities
        await self.db.flush()
        return {"status": "announced", "agent_id": str(agent_id)}
