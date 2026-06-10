import uuid
from typing import Any, Dict, List, Optional

from app.core.time import utc_now
from app.models.agents.agent_workspace import (
    AgentArtifactEvent,
    AgentSharedArtifact,
    AgentWorkspace,
)
from app.services.agents.workspace.artifact_permissions import ArtifactPermissionManager
from app.services.agents.workspace.artifact_versioning import ArtifactVersioningManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

SUPPORTED_ARTIFACT_TYPES = {
    "markdown_doc",
    "code_file",
    "json_plan",
    "eval_report",
    "compliance_evidence",
    "support_bundle",
    "workflow_definition",
    "prompt_baseline",
    "tool_definition"
}

class SharedArtifactRegistry:
    @staticmethod
    async def create_workspace(
        db: AsyncSession,
        name: str,
        tenant_id: str,
        owner_id: str,
        description: Optional[str] = None
    ) -> AgentWorkspace:
        """Creates a new collaborative workspace context."""
        workspace = AgentWorkspace(
            name=name,
            tenant_id=tenant_id,
            description=description,
            owner_id=owner_id,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(workspace)
        await db.commit()
        await db.refresh(workspace)
        return workspace

    @staticmethod
    async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID, tenant_id: str) -> AgentWorkspace | None:
        """Gets a workspace, enforcing strict tenant isolation."""
        stmt = select(AgentWorkspace).where(AgentWorkspace.id == workspace_id)
        result = await db.execute(stmt)
        workspace = result.scalar_one_or_none()
        if workspace:
            ArtifactPermissionManager.verify_tenant(workspace.tenant_id, tenant_id)
        return workspace

    @staticmethod
    async def list_workspaces(db: AsyncSession, tenant_id: str) -> List[AgentWorkspace]:
        """Lists workspaces under a tenant."""
        stmt = select(AgentWorkspace).where(AgentWorkspace.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_artifact(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        tenant_id: str,
        owner_id: str,
        name: str,
        artifact_type: str,
        content: str,
        creator_id: str,
        creator_type: str, # human|agent
        run_id: Optional[uuid.UUID] = None,
        step_id: Optional[uuid.UUID] = None,
        change_summary: Optional[str] = None,
        version_metadata: Optional[Dict[str, Any]] = None
    ) -> AgentSharedArtifact:
        """Creates a shared artifact inside a workspace with an initial immutable version."""
        # 1. Fetch and validate workspace
        workspace = await SharedArtifactRegistry.get_workspace(db, workspace_id, tenant_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found.")

        # 2. Validate artifact type
        if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
            raise ValueError(f"Unsupported artifact type '{artifact_type}'. Must be one of {SUPPORTED_ARTIFACT_TYPES}")

        # 3. Create the artifact skeleton
        artifact = AgentSharedArtifact(
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            name=name,
            artifact_type=artifact_type,
            owner_id=owner_id,
            status="draft",
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(artifact)
        await db.flush() # Populate artifact.id

        # 4. Create the initial version
        await ArtifactVersioningManager.create_version(
            db=db,
            artifact=artifact,
            content=content,
            creator_id=creator_id,
            creator_type=creator_type,
            run_id=run_id,
            step_id=step_id,
            change_summary=change_summary,
            version_metadata=version_metadata
        )

        # 5. Log artifact creation event
        event = AgentArtifactEvent(
            artifact_id=artifact.id,
            event_type="created",
            actor_id=creator_id,
            actor_type=creator_type,
            payload={"name": name, "artifact_type": artifact_type},
            created_at=utc_now()
        )
        db.add(event)
        await db.commit()

        await db.refresh(artifact)
        return artifact

    @staticmethod
    async def get_artifact(db: AsyncSession, artifact_id: uuid.UUID, tenant_id: str) -> AgentSharedArtifact | None:
        """Gets an artifact, enforcing strict tenant isolation."""
        stmt = select(AgentSharedArtifact).where(AgentSharedArtifact.id == artifact_id)
        result = await db.execute(stmt)
        artifact = result.scalar_one_or_none()
        if artifact:
            ArtifactPermissionManager.verify_tenant(artifact.tenant_id, tenant_id)
        return artifact

    @staticmethod
    async def list_artifacts(db: AsyncSession, workspace_id: uuid.UUID, tenant_id: str) -> List[AgentSharedArtifact]:
        """Lists artifacts inside a workspace, enforcing strict tenant isolation."""
        workspace = await SharedArtifactRegistry.get_workspace(db, workspace_id, tenant_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found.")

        stmt = select(AgentSharedArtifact).where(
            AgentSharedArtifact.workspace_id == workspace_id,
            AgentSharedArtifact.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
