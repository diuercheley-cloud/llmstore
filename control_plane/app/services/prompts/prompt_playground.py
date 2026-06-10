# Owner: agent-platform
import time
import uuid
from typing import Any, Dict

from app.models.agents.prompts import PromptPlaygroundRun, PromptTemplateVersion
from app.services.prompts.prompt_template_engine import PromptTemplateEngine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PromptPlayground:
    """
    Executes prompts for testing and iteration.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = PromptTemplateEngine()

    async def run_playground(self, version_id: uuid.UUID, variables: Dict[str, Any], created_by: str) -> PromptPlaygroundRun:
        stmt = select(PromptTemplateVersion).where(PromptTemplateVersion.id == version_id)
        res = await self.db.execute(stmt)
        version = res.scalar_one_or_none()
        if not version:
            raise ValueError("Version not found")

        # Render
        rendered_content = self.engine.render(version.content, variables)

        # Execute (Simulated call to LLM provider)
        start_time = time.time()
        # In real life, call self.llm_provider.generate(rendered_content, **version.provider_settings)
        output = f"Simulated output for rendered prompt: {rendered_content[:50]}..."
        latency_ms = int((time.time() - start_time) * 1000)

        run = PromptPlaygroundRun(
            version_id=version_id,
            variables=variables,
            output=output,
            latency_ms=latency_ms,
            token_usage={"total": 100},
            created_by=created_by
        )
        self.db.add(run)
        await self.db.flush()
        return run
