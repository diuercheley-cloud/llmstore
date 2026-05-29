# Owner: agent-platform
import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentRun
from app.models.agent_canary import AgentShadowRun, AgentCanaryAssignment
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class ShadowRunner:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def launch_shadow(self, primary_run_id: uuid.UUID, assignment: AgentCanaryAssignment) -> Optional[uuid.UUID]:
        """
        Launches a parallel shadow run for an existing primary run.
        """
        if not self.settings.agent_shadow_mode_enabled:
            return None

        primary_run = await self.db.get(AgentRun, primary_run_id)
        if not primary_run:
            return None

        # Create shadow run
        shadow_run = AgentRun(
            agent_id=assignment.canary_agent_id,
            tenant_id=primary_run.tenant_id,
            user_id=primary_run.user_id,
            status="queued",
            input_text=primary_run.input_text
        )
        self.db.add(shadow_run)
        await self.db.flush()

        # Record shadow relationship
        record = AgentShadowRun(
            assignment_id=assignment.id,
            primary_run_id=primary_run_id,
            shadow_run_id=shadow_run.id,
            status="running"
        )
        self.db.add(record)
        await self.db.commit()

        logger.info(f"Launched shadow run {shadow_run.id} for primary run {primary_run_id}")
        return shadow_run.id
