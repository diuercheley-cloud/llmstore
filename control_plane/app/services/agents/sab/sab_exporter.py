# Owner: agent-platform
import hashlib
import json
import uuid

from app.models.agents.agents import AgentDefinition
from sqlalchemy.ext.asyncio import AsyncSession

from .sab_manifest import AgentSABManifest


class SABExporter:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_agent(self, agent_id: uuid.UUID) -> AgentSABManifest:
        agent = await self.db.get(AgentDefinition, agent_id)
        if not agent:
            raise ValueError("Agent not found")

        # Basic manifest
        manifest_data = {
            "agent_id": str(agent.id),
            "name": agent.name,
            "version": agent.version,
            "instructions": agent.instructions,
            "tool_schemas": [], # In real app: fetch from ToolRegistry
            "memory_policy": {}, # In real app: fetch from MemoryPolicyService
            "provenance": {
                "source_tenant": agent.tenant_id,
                "exported_by": "system"
            }
        }

        manifest = AgentSABManifest(**manifest_data)

        # Create checksum of the core payload using canonical representation
        data_to_hash = manifest.model_dump(exclude={"checksums", "signature"})
        payload = json.dumps(data_to_hash, sort_keys=True).encode()
        checksum = hashlib.sha256(payload).hexdigest()
        
        manifest.checksums = {"manifest": checksum}
        
        # Mock signature
        manifest.signature = f"sig:{checksum}:prod_key"

        return manifest
