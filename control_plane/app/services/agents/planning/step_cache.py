# Owner: agent-platform
import logging
import uuid
from datetime import timedelta
from typing import Any, Dict, Optional

from app.core.time import utc_now
from app.models.agents.agents import AgentStepCacheEntry, AgentTool
from app.services.agents import agent_state
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class StepCache:
    def __init__(self, db: AsyncSession, ttl_hours: int = 24):
        self.db = db
        self.ttl_hours = ttl_hours

    async def get_cached_step(
        self,
        agent_id: uuid.UUID,
        tenant_id: str,
        step_type: str,
        input_data: Any,
        model_version: Optional[str] = None,
        tool_version: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Retrieves a cached step if it exists and hasn't expired.
        input_data should include history to ensure context-aware caching.
        """
        input_hash = agent_state.compute_sha256(input_data)
        
        stmt = select(AgentStepCacheEntry).where(
            AgentStepCacheEntry.agent_id == agent_id,
            AgentStepCacheEntry.tenant_id == tenant_id,
            AgentStepCacheEntry.step_type == step_type,
            AgentStepCacheEntry.input_hash == input_hash,
            AgentStepCacheEntry.expires_at > utc_now(),
        )
        
        if model_version:
            stmt = stmt.where(AgentStepCacheEntry.model_version == model_version)
        if tool_version:
            stmt = stmt.where(AgentStepCacheEntry.tool_version == tool_version)
            
        res = await self.db.execute(stmt)
        entry = res.scalar_one_or_none()
        
        if entry:
            logger.info(f"Step cache hit for agent {agent_id}, step_type {step_type}")
            return entry.output_data
        
        return None

    async def set_cached_step(
        self,
        agent_id: uuid.UUID,
        tenant_id: str,
        step_type: str,
        input_data: Any,
        output_data: Dict,
        model_version: Optional[str] = None,
        tool_version: Optional[str] = None,
        ttl_hours: Optional[int] = None,
    ):
        """
        Caches a step result if it's considered cacheable (no side effects).
        """
        is_cacheable = await self._is_cacheable(step_type, output_data)
        if not is_cacheable:
            logger.info(f"Step type {step_type} or output is not cacheable (side effects detected)")
            return

        input_hash = agent_state.compute_sha256(input_data)
        expires_at = utc_now() + timedelta(hours=ttl_hours or self.ttl_hours)
        
        # Check if already exists to avoid duplicates
        stmt = select(AgentStepCacheEntry).where(
            AgentStepCacheEntry.agent_id == agent_id,
            AgentStepCacheEntry.tenant_id == tenant_id,
            AgentStepCacheEntry.step_type == step_type,
            AgentStepCacheEntry.input_hash == input_hash,
            AgentStepCacheEntry.model_version == model_version,
            AgentStepCacheEntry.tool_version == tool_version
        )
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        
        if existing:
            existing.output_data = output_data
            existing.expires_at = expires_at
        else:
            entry = AgentStepCacheEntry(
                agent_id=agent_id,
                tenant_id=tenant_id,
                step_type=step_type,
                input_hash=input_hash,
                output_data=output_data,
                model_version=model_version,
                tool_version=tool_version,
                expires_at=expires_at,
            )
            self.db.add(entry)
        
        await self.db.flush()
        logger.info(f"Cached step for agent {agent_id}, step_type {step_type}")

    async def _is_cacheable(self, step_type: str, output_data: Dict) -> bool:
        """
        Heuristic to determine if a step is cacheable.
        Steps with side effects (like database writes or external API calls with side effects) 
        should not be cached if the cache would skip the side effect.
        """
        # If the decision is to call a tool, we check if the tool has side effects.
        # However, the user said "cache hit evita model call". 
        # If we cache the MODEL CALL, we still execute the tool.
        # But if we cache the TOOL RESULT, we skip the tool execution.
        
        # Based on "Não cachear steps com side effects", we should avoid caching
        # any step that performs a write, destructive, or external action.
        
        decision_type = output_data.get("type", "final")
        
        if decision_type == "tool_call":
            tool_name = output_data.get("tool_name")
            if tool_name:
                stmt = select(AgentTool).where(AgentTool.name == tool_name)
                res = await self.db.execute(stmt)
                tool = res.scalar_one_or_none()
                if tool and tool.side_effect_level not in ("none", "read"):
                    return False
        
        if decision_type in ("memory_write", "memory_read", "handoff"):
            return False
            
        return True

    async def invalidate_cache(self, agent_id: uuid.UUID, tenant_id: str):
        """
        Invalidates all cache entries for a given agent and tenant.
        """
        # In a real system, we'd use a DELETE statement. 
        # For this implementation, we'll fetch and delete or use a bulk delete if supported.
        from sqlalchemy import delete
        stmt = delete(AgentStepCacheEntry).where(
            AgentStepCacheEntry.agent_id == agent_id,
            AgentStepCacheEntry.tenant_id == tenant_id
        )
        await self.db.execute(stmt)
        await self.db.flush()
        logger.info(f"Invalidated cache for agent {agent_id}, tenant {tenant_id}")
