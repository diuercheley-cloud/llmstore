# Owner: agent-platform
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentDefinition
from .sab_manifest import AgentSABManifest
from .sab_verifier import SABVerifier

class SABImporter:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.verifier = SABVerifier()

    async def import_agent(self, manifest: AgentSABManifest, tenant_id: str) -> AgentDefinition:
        # 1. Verify
        is_valid, reason = self.verifier.verify(manifest)
        if not is_valid:
            raise ValueError(f"Import failed: {reason}")

        # 2. Create Agent as Draft
        agent = AgentDefinition(
            tenant_id=tenant_id,
            name=f"[Imported] {manifest.name}",
            version=manifest.version,
            instructions=manifest.instructions,
            model_id="gpt-4o", # Default for import
            owner="imported-system",
            status="draft" # Never activate automatically
        )
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent
