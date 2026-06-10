# Owner: agent-platform
import hashlib
import os
import uuid
from pathlib import Path

from app.models.agents.agent_tool_synthesis import AgentSandboxArtifact
from sqlalchemy.ext.asyncio import AsyncSession

from .sandbox_policy import SandboxPolicyEngine


class SandboxArtifactService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.policy = SandboxPolicyEngine()
        self.base_path = Path(os.environ.get("AGENT_ARTIFACTS_PATH", "/tmp/agent_artifacts"))

    async def record_artifact(
        self,
        session_id: uuid.UUID,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> AgentSandboxArtifact:
        self.policy.validate_artifact_content(content)
        self.base_path.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(content).hexdigest()
        safe_name = hashlib.sha256(f"{session_id}:{filename}".encode("utf-8")).hexdigest()
        storage_path = self.base_path / safe_name
        storage_path.write_bytes(content)

        artifact = AgentSandboxArtifact(
            session_id=session_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            storage_path=str(storage_path),
        )
        self.db.add(artifact)
        await self.db.commit()
        await self.db.refresh(artifact)
        artifact.__dict__["content_hash"] = digest
        artifact.__dict__["provenance"] = {"provider": "sandbox", "filename": filename}
        return artifact
