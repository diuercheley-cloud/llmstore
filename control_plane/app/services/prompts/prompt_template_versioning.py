# Owner: agent-platform
import logging
import uuid

from app.models.agents.prompts import PromptTemplateVersion
from app.services.prompts.prompt_template_validator import PromptTemplateValidator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class VersionAlreadyPromotedError(RuntimeError):
    pass


class VersionImmutableError(RuntimeError):
    pass


class PromptTemplateVersioningService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.validator = PromptTemplateValidator()

    async def get_version(self, version_id: uuid.UUID) -> PromptTemplateVersion | None:
        stmt = select(PromptTemplateVersion).where(PromptTemplateVersion.id == version_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def promote_to_staging(self, version_id: uuid.UUID) -> bool:
        version = await self.get_version(version_id)
        if not version:
            return False

        validation = self.validator.validate_version_promotion(version, "staging")
        if not validation.valid:
            logger.warning(f"Promotion to staging blocked for {version_id}: {validation.errors}")
            return False

        if version.status == "production":
            raise VersionAlreadyPromotedError("Cannot demote a production version to staging")

        version.status = "staging"
        await self.db.flush()
        logger.info(f"Promoted version {version_id} to staging")
        return True

    async def promote_to_production(self, version_id: uuid.UUID) -> bool:
        version = await self.get_version(version_id)
        if not version:
            return False

        validation = self.validator.validate_version_promotion(version, "production")
        if not validation.valid:
            logger.warning(f"Promotion to production blocked for {version_id}: {validation.errors}")
            return False

        version.status = "production"
        await self.db.flush()
        logger.info(f"Promoted version {version_id} to production")
        return True

    async def rollback(self, template_id: uuid.UUID, to_version_id: uuid.UUID) -> bool:
        from app.services.prompts.prompt_template_registry import (
            PromptTemplateRegistryService,
        )

        registry = PromptTemplateRegistryService(self.db)
        target = await self.get_version(to_version_id)
        if not target:
            return False

        template = await registry.get_template(template_id)
        if not template:
            return False

        template.active_version_id = to_version_id
        await self.db.flush()
        logger.info(f"Rolled back template {template_id} to version {to_version_id}")
        return True

    async def archive_version(self, version_id: uuid.UUID) -> bool:
        version = await self.get_version(version_id)
        if not version:
            return False
        if version.status == "production":
            raise VersionImmutableError(
                "Cannot archive a production version. Promote a new version first."
            )
        version.status = "archived"
        await self.db.flush()
        return True
