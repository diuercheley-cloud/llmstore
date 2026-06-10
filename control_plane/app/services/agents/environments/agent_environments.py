import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.models.agents.agent_environments import AgentEnvironmentVersion
from app.models.agents.agents import AgentDefinition, AgentRegistryEntry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("agent_environments")


class AgentEnvironmentsService:
    @classmethod
    async def get_environments(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: str
    ) -> List[Dict[str, Any]]:
        """Returns the version mapping across all environments (dev, staging, production) for an agent."""
        try:
            agent_uuid = uuid.UUID(agent_id)
        except ValueError:
            return []

        # Ensure agent registry entry exists and belongs to tenant
        stmt_reg = select(AgentRegistryEntry).where(
            (AgentRegistryEntry.id == agent_uuid) | (AgentRegistryEntry.agent_id == agent_uuid)
        )
        res_reg = await db.execute(stmt_reg)
        reg = res_reg.scalar_one_or_none()
        if not reg:
            return []
        
        # Verify tenant if agent registry contains allowed_tenants
        if reg.allowed_tenants:
            if tenant_id not in reg.allowed_tenants:
                return []

        stmt = select(AgentEnvironmentVersion).where(
            AgentEnvironmentVersion.tenant_id == tenant_id,
            AgentEnvironmentVersion.agent_id == reg.id
        )
        res = await db.execute(stmt)
        versions = res.scalars().all()

        envs = ["dev", "staging", "production"]
        mapping = {env: None for env in envs}

        for ev in versions:
            # Fetch Agent Definition name/version details
            stmt_def = select(AgentDefinition).where(AgentDefinition.id == ev.version_id)
            res_def = await db.execute(stmt_def)
            adef = res_def.scalar_one_or_none()
            
            mapping[ev.environment] = {
                "version_id": str(ev.version_id),
                "name": adef.name if adef else "Unknown",
                "version_tag": adef.version if adef else "1.0",
                "deployed_at": ev.deployed_at.isoformat(),
                "previous_version_id": str(ev.previous_version_id) if ev.previous_version_id else None
            }

        return [
            {
                "environment": env,
                "deployed_version": mapping[env]
            }
            for env in envs
        ]

    @classmethod
    async def deploy_to_environment(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: uuid.UUID,
        version_id: uuid.UUID,
        environment: str
    ) -> AgentEnvironmentVersion:
        """Deploys a specific agent version to the environment, capturing rollback points."""
        env_lower = environment.lower().strip()

        # Check if version already deployed in this environment
        stmt = select(AgentEnvironmentVersion).where(
            AgentEnvironmentVersion.tenant_id == tenant_id,
            AgentEnvironmentVersion.agent_id == agent_id,
            AgentEnvironmentVersion.environment == env_lower
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()

        if record:
            # We record a rollback point if deploying a different version
            if record.version_id != version_id:
                record.previous_version_id = record.version_id
                record.version_id = version_id
                record.deployed_at = datetime.now(timezone.utc)
        else:
            record = AgentEnvironmentVersion(
                tenant_id=tenant_id,
                agent_id=agent_id,
                environment=env_lower,
                version_id=version_id,
                previous_version_id=None,
                deployed_at=datetime.now(timezone.utc)
            )
            db.add(record)

        await db.commit()
        return record

    @classmethod
    async def rollback_environment(
        cls,
        db: AsyncSession,
        tenant_id: str,
        agent_id: str,
        environment: str
    ) -> Dict[str, Any]:
        """Rolls back the environment to the previous deployed version."""
        try:
            agent_uuid = uuid.UUID(agent_id)
        except ValueError:
            return {"status": "error", "message": "Invalid agent ID format."}

        env_lower = environment.lower().strip()

        # Resolve registry entry first
        stmt_reg = select(AgentRegistryEntry).where(
            (AgentRegistryEntry.id == agent_uuid) | (AgentRegistryEntry.agent_id == agent_uuid)
        )
        res_reg = await db.execute(stmt_reg)
        reg = res_reg.scalar_one_or_none()
        if not reg:
            return {"status": "error", "message": "Agent registry entry not found."}

        stmt = select(AgentEnvironmentVersion).where(
            AgentEnvironmentVersion.tenant_id == tenant_id,
            AgentEnvironmentVersion.agent_id == reg.id,
            AgentEnvironmentVersion.environment == env_lower
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            return {"status": "error", "message": f"No deployment history found in {environment} for this agent."}

        if not record.previous_version_id:
            return {"status": "error", "message": "No rollback point exists for this environment."}

        # Swap current and previous versions
        current_active = record.version_id
        record.version_id = record.previous_version_id
        record.previous_version_id = current_active
        record.deployed_at = datetime.now(timezone.utc)

        await db.commit()

        # Fetch details of newly restored version
        stmt_def = select(AgentDefinition).where(AgentDefinition.id == record.version_id)
        res_def = await db.execute(stmt_def)
        adef = res_def.scalar_one_or_none()

        return {
            "status": "success",
            "message": f"Rolled back {environment} environment successfully.",
            "restored_version_id": str(record.version_id),
            "restored_version_tag": adef.version if adef else "1.0"
        }
