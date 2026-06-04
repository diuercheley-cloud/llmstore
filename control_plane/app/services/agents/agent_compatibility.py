"""
Owner: agent-platform
Status: beta
"""
import logging
import uuid
from typing import Any, Dict

from app.core.config import get_settings
from app.models.agents import AgentBundleCompatibility
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

class AgentCompatibilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def check_compatibility(self, version_id: uuid.UUID, platform_version: str) -> Dict[str, Any]:
        res = await self.db.execute(select(AgentBundleCompatibility).where(AgentBundleCompatibility.version_id == version_id))
        comp = res.scalar_one_or_none()
        
        if not comp:
             return {"compatible": True, "reason": "No compatibility rules defined"}

        # Semantic version check (mock)
        if platform_version < comp.platform_version_min:
             return {"compatible": False, "reason": f"Platform version {platform_version} below minimum {comp.platform_version_min}"}

        if comp.platform_version_max and platform_version > comp.platform_version_max:
             return {"compatible": False, "reason": f"Platform version {platform_version} above maximum {comp.platform_version_max}"}

        return {"compatible": True}
