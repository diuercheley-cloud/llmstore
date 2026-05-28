import uuid
import hashlib
import re
from typing import Optional, Dict, Any
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_workspace import AgentSharedArtifact, AgentArtifactVersion, AgentArtifactEvent
from app.core.time import utc_now

class ArtifactVersioningManager:
    @staticmethod
    def calculate_hash(content: str) -> str:
        """Helper to calculate SHA-256 hash of the content to ensure integrity."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def sanitize_content(content: str, artifact_type: str) -> str:
        """Sanitizes sensitive information from content before export (e.g. API keys, secrets)."""
        # Match typical API Keys/Secrets, OpenAI keys, password fields, etc.
        sanitized = content
        
        # 1. Mask OpenAI API keys
        sanitized = re.sub(r'sk-[a-zA-Z0-9]{32,}', 'sk-***[REDACTED_API_KEY]***', sanitized)
        
        # 2. Mask JSON-like key-value pairs (quoted keys)
        sanitized = re.sub(
            r'(?i)"(api_key|apikey|secret|password|passwd|token|private_key)"\s*:\s*"[^"]+"',
            r'"\1": "***[REDACTED_SECRET]***"',
            sanitized
        )
        
        # 3. Mask unquoted config/env key-value pairs (excluding "token" to avoid text sentence conflicts)
        sanitized = re.sub(
            r'(?i)\b(api_key|apikey|secret|password|passwd|private_key)\s*[:=]\s*["\']([^"\']+)["\']',
            r'\1: "***[REDACTED_SECRET]***"',
            sanitized
        )
            
        return sanitized

    @staticmethod
    async def create_version(
        db: AsyncSession,
        artifact: AgentSharedArtifact,
        content: str,
        creator_id: str,
        creator_type: str, # human|agent
        run_id: Optional[uuid.UUID] = None,
        step_id: Optional[uuid.UUID] = None,
        change_summary: Optional[str] = None,
        version_metadata: Optional[Dict[str, Any]] = None
    ) -> AgentArtifactVersion:
        """Creates a new immutable version of the artifact, updating the artifact's current version pointers."""
        # Calculate new version number
        stmt = select(func.max(AgentArtifactVersion.version_number)).where(AgentArtifactVersion.artifact_id == artifact.id)
        result = await db.execute(stmt)
        max_version = result.scalar() or 0
        new_version_number = max_version + 1

        content_hash = ArtifactVersioningManager.calculate_hash(content)

        # Enforce creator type
        if creator_type not in ["human", "agent"]:
            raise ValueError("creator_type must be either 'human' or 'agent'.")

        version = AgentArtifactVersion(
            artifact_id=artifact.id,
            version_number=new_version_number,
            content=content,
            content_hash=content_hash,
            creator_id=creator_id,
            creator_type=creator_type,
            run_id=run_id,
            step_id=step_id,
            change_summary=change_summary,
            version_metadata=version_metadata,
            created_at=utc_now()
        )
        db.add(version)
        await db.flush() # Populate version.id

        # Update current version in the artifact
        artifact.current_version_id = version.id
        db.add(artifact)

        # Log event
        event = AgentArtifactEvent(
            artifact_id=artifact.id,
            event_type="updated" if new_version_number > 1 else "created",
            actor_id=creator_id,
            actor_type=creator_type,
            payload={
                "version_id": str(version.id),
                "version_number": new_version_number,
                "run_id": str(run_id) if run_id else None,
                "step_id": str(step_id) if step_id else None,
            },
            created_at=utc_now()
        )
        db.add(event)

        await db.commit()
        await db.refresh(version)
        await db.refresh(artifact)
        return version
