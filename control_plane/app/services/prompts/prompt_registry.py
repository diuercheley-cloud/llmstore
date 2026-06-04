# Owner: agent-platform
import logging
import uuid
from typing import Dict, List, Optional

from app.models.prompts import PromptTemplate, PromptTemplateVersion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class PromptRegistry:
    """
    Manages the lifecycle of prompt templates and their versions.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(self, tenant_id: str, name: str, description: str = None, variable_schema: Dict = None) -> PromptTemplate:
        template = PromptTemplate(
            tenant_id=tenant_id,
            name=name,
            description=description,
            variable_schema=variable_schema or {}
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def get_template(self, template_id: uuid.UUID) -> Optional[PromptTemplate]:
        stmt = select(PromptTemplate).where(PromptTemplate.id == template_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_templates(self, tenant_id: str) -> List[PromptTemplate]:
        stmt = select(PromptTemplate).where(PromptTemplate.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create_version(self, template_id: uuid.UUID, content: str, created_by: str, version_tag: str, provider_settings: Dict = None) -> PromptTemplateVersion:
        # Check if version tag exists
        stmt = select(PromptTemplateVersion).where(
            PromptTemplateVersion.template_id == template_id,
            PromptTemplateVersion.version_tag == version_tag
        )
        res = await self.db.execute(stmt)
        if res.scalar_one_or_none():
            raise ValueError(f"Version tag {version_tag} already exists for template {template_id}")

        version = PromptTemplateVersion(
            template_id=template_id,
            content=content,
            created_by=created_by,
            version_tag=version_tag,
            provider_settings=provider_settings or {},
            status="draft"
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def set_active_version(self, template_id: uuid.UUID, version_id: uuid.UUID):
        stmt = select(PromptTemplate).where(PromptTemplate.id == template_id)
        res = await self.db.execute(stmt)
        template = res.scalar_one_or_none()
        if not template:
            raise ValueError("Template not found")
        
        template.active_version_id = version_id
        await self.db.flush()
