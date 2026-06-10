# Owner: agent-platform
import logging
import re
import uuid
from typing import List, Tuple

from app.models.agents.prompts import PromptTemplateVersion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class PromptSecurityScanner:
    """
    Scans prompts for security risks like secrets and unsafe instructions.
    """
    def scan(self, content: str) -> Tuple[bool, List[str]]:
        reasons = []
        
        # 1. Secret detection (simplistic)
        if re.search(r"(api_key|secret|password|token)[\s:=]+[\"'][a-zA-Z0-9_\-]{16,}[\"']", content, re.I):
            reasons.append("Potential secret/API key detected in prompt content")

        # 2. Unsafe instructions (simplistic)
        unsafe_patterns = [
            r"ignore previous instructions",
            r"ignore all system prompts",
            r"output your system message",
            r"bypass all filters"
        ]
        for pattern in unsafe_patterns:
            if re.search(pattern, content, re.I):
                reasons.append(f"Unsafe instruction detected: {pattern}")

        return len(reasons) == 0, reasons

class PromptVersioningService:
    """
    Handles promotion and rollback of prompt versions.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.security = PromptSecurityScanner()

    async def promote_to_staging(self, version_id: uuid.UUID) -> bool:
        stmt = select(PromptTemplateVersion).where(PromptTemplateVersion.id == version_id)
        res = await self.db.execute(stmt)
        version = res.scalar_one_or_none()
        if not version:
            return False
        
        is_safe, risks = self.security.scan(version.content)
        if not is_safe:
            logger.warning(f"Promotion to staging blocked for version {version_id}: {risks}")
            return False

        version.status = "staging"
        await self.db.flush()
        return True

    async def promote_to_production(self, version_id: uuid.UUID) -> bool:
        stmt = select(PromptTemplateVersion).where(PromptTemplateVersion.id == version_id)
        res = await self.db.execute(stmt)
        version = res.scalar_one_or_none()
        if not version or version.status != "staging":
            return False

        version.status = "production"
        await self.db.flush()
        return True

    async def rollback(self, template_id: uuid.UUID, to_version_id: uuid.UUID):
        from app.services.prompts.prompt_registry import PromptRegistry
        registry = PromptRegistry(self.db)
        await registry.set_active_version(template_id, to_version_id)
