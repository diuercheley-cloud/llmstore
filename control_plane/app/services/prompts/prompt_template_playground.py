# Owner: agent-platform
import logging
import time
import uuid
from typing import Any

from app.models.agents.prompts import (
    PromptPlaygroundRun,
    PromptTemplateVersion,
)
from app.services.prompts.prompt_template_renderer import PromptTemplateRenderer
from app.services.prompts.prompt_template_validator import PromptTemplateValidator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PromptTemplatePlaygroundService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.renderer = PromptTemplateRenderer()
        self.validator = PromptTemplateValidator()

    async def render_only(
        self,
        version_id: uuid.UUID,
        variables: dict[str, Any],
        declared_vars: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        stmt = select(PromptTemplateVersion).where(PromptTemplateVersion.id == version_id)
        res = await self.db.execute(stmt)
        version = res.scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        rendered, vhash, ohash, chash = self.renderer.render(
            version.content,
            variables,
            declared_vars=declared_vars,
        )

        return {
            "version_id": str(version_id),
            "version_tag": version.version_tag,
            "rendered": rendered,
            "variables_hash": vhash,
            "output_hash": ohash,
            "rendered_content_hash": chash,
        }

    async def run_playground(
        self,
        version_id: uuid.UUID,
        variables: dict[str, Any],
        created_by: str,
        declared_vars: list[dict[str, Any]] | None = None,
    ) -> PromptPlaygroundRun:
        stmt = select(PromptTemplateVersion).where(PromptTemplateVersion.id == version_id)
        res = await self.db.execute(stmt)
        version = res.scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        rendered, vhash, ohash, chash = self.renderer.render(
            version.content,
            variables,
            declared_vars=declared_vars,
        )

        start_time = time.time()
        token_estimate = len(rendered) // 4
        output = f"[Prompt rendered successfully]\n\n{rendered}"
        latency_ms = int((time.time() - start_time) * 1000)

        run = PromptPlaygroundRun(
            version_id=version_id,
            variables=variables,
            output=output,
            latency_ms=latency_ms,
            token_usage={"estimated_tokens": token_estimate, "total": token_estimate},
            created_by=created_by,
        )
        self.db.add(run)
        await self.db.flush()
        return run
