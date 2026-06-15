# Owner: agent-platform
import logging
import uuid
from typing import Any

from app.models.agents.prompts import (
    PromptTemplate,
    PromptTemplateRenderEvent,
    PromptTemplateVariable,
    PromptTemplateVersion,
)
from app.services.prompts.prompt_template_validator import PromptTemplateValidator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PromptTemplateRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.validator = PromptTemplateValidator()

    async def create_template(
        self,
        tenant_id: str,
        name: str,
        description: str | None = None,
    ) -> PromptTemplate:
        template = PromptTemplate(
            tenant_id=tenant_id,
            name=name,
            description=description,
            variable_schema={},
        )
        self.db.add(template)
        await self.db.flush()
        logger.info(f"Created prompt template {template.id} ({name})")
        return template

    async def get_template(
        self, template_id: uuid.UUID, tenant_id: str | None = None
    ) -> PromptTemplate | None:
        stmt = select(PromptTemplate).where(PromptTemplate.id == template_id)
        if tenant_id:
            stmt = stmt.where(PromptTemplate.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_templates(self, tenant_id: str) -> list[PromptTemplate]:
        stmt = (
            select(PromptTemplate)
            .where(PromptTemplate.tenant_id == tenant_id)
            .order_by(PromptTemplate.updated_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def declare_variable(
        self,
        template_id: uuid.UUID,
        name: str,
        var_type: str = "string",
        required: bool = True,
        default: str | None = None,
        description: str | None = None,
    ) -> PromptTemplateVariable:
        validation = self.validator.validate_variable_declaration(name, var_type)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        var = PromptTemplateVariable(
            template_id=template_id,
            name=name,
            var_type=var_type,
            required=required,
            default=default,
            description=description,
        )
        self.db.add(var)
        await self.db.flush()
        return var

    async def get_declared_variables(self, template_id: uuid.UUID) -> list[PromptTemplateVariable]:
        stmt = (
            select(PromptTemplateVariable)
            .where(PromptTemplateVariable.template_id == template_id)
            .order_by(PromptTemplateVariable.created_at.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create_version(
        self,
        template_id: uuid.UUID,
        content: str,
        created_by: str,
        version_tag: str,
        provider_settings: dict[str, Any] | None = None,
    ) -> PromptTemplateVersion:
        content_validation = self.validator.validate_template_content(content)
        if not content_validation.valid:
            raise ValueError("; ".join(content_validation.errors))

        existing = await self.db.execute(
            select(PromptTemplateVersion).where(
                PromptTemplateVersion.template_id == template_id,
                PromptTemplateVersion.version_tag == version_tag,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Version tag '{version_tag}' already exists for this template")

        version = PromptTemplateVersion(
            template_id=template_id,
            content=content,
            created_by=created_by,
            version_tag=version_tag,
            provider_settings=provider_settings or {},
            status="draft",
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def get_version(self, version_id: uuid.UUID) -> PromptTemplateVersion | None:
        stmt = select(PromptTemplateVersion).where(PromptTemplateVersion.id == version_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_versions(self, template_id: uuid.UUID) -> list[PromptTemplateVersion]:
        stmt = (
            select(PromptTemplateVersion)
            .where(PromptTemplateVersion.template_id == template_id)
            .order_by(PromptTemplateVersion.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def set_active_version(
        self, template_id: uuid.UUID, version_id: uuid.UUID
    ) -> PromptTemplate:
        template = await self.get_template(template_id)
        if not template:
            raise ValueError("Template not found")
        version = await self.get_version(version_id)
        if not version:
            raise ValueError("Version not found")
        template.active_version_id = version_id
        await self.db.flush()
        return template

    async def record_render_event(
        self,
        template_id: uuid.UUID | None,
        version_id: uuid.UUID,
        tenant_id: str,
        variables_hash: str,
        output_hash: str,
        rendered_content_hash: str,
        agent_run_id: uuid.UUID | None = None,
        agent_id: uuid.UUID | None = None,
    ) -> PromptTemplateRenderEvent:
        event = PromptTemplateRenderEvent(
            template_id=template_id,
            version_id=version_id,
            tenant_id=tenant_id,
            variables_hash=variables_hash,
            output_hash=output_hash,
            rendered_content_hash=rendered_content_hash,
            agent_run_id=agent_run_id,
            agent_id=agent_id,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def count_render_events(self, template_id: uuid.UUID, limit: int = 100) -> list:
        stmt = (
            select(PromptTemplateRenderEvent)
            .where(PromptTemplateRenderEvent.template_id == template_id)
            .order_by(PromptTemplateRenderEvent.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
