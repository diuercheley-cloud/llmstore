# Owner: agent-platform
# Surface: admin
import uuid
from typing import List

from app.api.deps import get_admin_token, get_db
from app.core.config import get_settings
from app.models.agent_workspace import (
    AgentArtifactEvent,
    AgentArtifactVersion,
)
from app.schemas.agent_workspace import (
    ArtifactCommentCreate,
    ArtifactCommentRead,
    ArtifactCreate,
    ArtifactDiffResponse,
    ArtifactEventRead,
    ArtifactLockAcquire,
    ArtifactLockRead,
    ArtifactRead,
    ArtifactReviewCreate,
    ArtifactReviewRead,
    ArtifactVersionCreate,
    ArtifactVersionRead,
    WorkspaceCreate,
    WorkspaceRead,
)
from app.services.agents.workspace import (
    ArtifactDiffManager,
    ArtifactLockManager,
    ArtifactReviewManager,
    ArtifactVersioningManager,
    SharedArtifactRegistry,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter()

# Dependency checks for feature flags
def require_shared_workspace():
    settings = get_settings()
    if not settings.agent_shared_workspace_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shared workspace is disabled by feature flag AGENT_SHARED_WORKSPACE_ENABLED."
        )

def require_shared_artifacts():
    settings = get_settings()
    if not settings.agent_shared_artifacts_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shared artifacts are disabled by feature flag AGENT_SHARED_ARTIFACTS_ENABLED."
        )

def require_collaborative_editing():
    settings = get_settings()
    if not settings.agent_collaborative_editing_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collaborative editing is disabled by feature flag AGENT_COLLABORATIVE_EDITING_ENABLED."
        )


@router.post("/admin/agents/workspaces", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_workspace)
):
    """Creates a new agent collaborative workspace."""
    workspace = await SharedArtifactRegistry.create_workspace(
        db=db,
        name=payload.name,
        tenant_id=payload.tenant_id or "default",
        owner_id="admin", # Default creator is admin
        description=payload.description
    )
    return workspace


@router.get("/admin/agents/workspaces", response_model=List[WorkspaceRead])
async def list_workspaces(
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_workspace)
):
    """Lists all workspaces under a tenant."""
    workspaces = await SharedArtifactRegistry.list_workspaces(db, tenant_id)
    return workspaces


@router.post("/admin/agents/workspaces/{id}/artifacts", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    id: uuid.UUID,
    payload: ArtifactCreate,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff_ws = Depends(require_shared_workspace),
    _ff_art = Depends(require_shared_artifacts)
):
    """Creates a shared artifact in a workspace with an initial version."""
    try:
        artifact = await SharedArtifactRegistry.create_artifact(
            db=db,
            workspace_id=id,
            tenant_id=tenant_id,
            owner_id=payload.creator_id,
            name=payload.name,
            artifact_type=payload.artifact_type,
            content=payload.content,
            creator_id=payload.creator_id,
            creator_type=payload.creator_type,
            run_id=payload.run_id,
            step_id=payload.step_id,
            change_summary=payload.change_summary,
            version_metadata=payload.version_metadata
        )
        return artifact
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/admin/agents/artifacts/{id}", response_model=ArtifactRead)
async def get_artifact(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_artifacts)
):
    """Gets an artifact's details, enforcing tenant isolation."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")
    return artifact


@router.post("/admin/agents/artifacts/{id}/versions", response_model=ArtifactVersionRead, status_code=status.HTTP_201_CREATED)
async def create_artifact_version(
    id: uuid.UUID,
    payload: ArtifactVersionCreate,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff_art = Depends(require_shared_artifacts),
    _ff_edit = Depends(require_collaborative_editing)
):
    """Creates a new immutable version of an artifact, enforcing locking and provenance validation."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    # 1. Enforce pessimistic lock checks
    try:
        await ArtifactLockManager.check_write_allowed(db, id, payload.creator_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # 2. Enforce optimistic lock checking
    if payload.expected_version_id is not None:
        try:
            ArtifactLockManager.verify_optimistic_lock(artifact, expected_version_id=payload.expected_version_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # 3. Create version
    try:
        version = await ArtifactVersioningManager.create_version(
            db=db,
            artifact=artifact,
            content=payload.content,
            creator_id=payload.creator_id,
            creator_type=payload.creator_type,
            run_id=payload.run_id,
            step_id=payload.step_id,
            change_summary=payload.change_summary,
            version_metadata=payload.version_metadata
        )
        return version
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/admin/agents/artifacts/{id}/diff", response_model=ArtifactDiffResponse)
async def get_artifact_diff(
    id: uuid.UUID,
    from_version: int = Query(..., description="Starting version number"),
    to_version: int = Query(..., description="Ending version number"),
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_artifacts)
):
    """Generates a text/unified and structured line-by-line diff between two artifact versions."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    try:
        v_from = await ArtifactDiffManager.get_version_by_number(db, id, from_version)
        v_to = await ArtifactDiffManager.get_version_by_number(db, id, to_version)
        diff_res = ArtifactDiffManager.compute_diff(v_from.content, v_to.content)
        return diff_res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/admin/agents/artifacts/{id}/lock", response_model=ArtifactLockRead)
async def lock_artifact(
    id: uuid.UUID,
    payload: ArtifactLockAcquire,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff_art = Depends(require_shared_artifacts),
    _ff_edit = Depends(require_collaborative_editing)
):
    """Acquires a pessimistic lock on an artifact."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    try:
        lock = await ArtifactLockManager.acquire_lock(
            db=db,
            artifact_id=id,
            holder_id=payload.holder_id,
            holder_type=payload.holder_type,
            lock_type=payload.lock_type or "exclusive",
            expires_in_seconds=payload.expires_in_seconds or 300
        )
        return lock
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/admin/agents/artifacts/{id}/unlock")
async def unlock_artifact(
    id: uuid.UUID,
    holder_id: str = Query(...),
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff_art = Depends(require_shared_artifacts),
    _ff_edit = Depends(require_collaborative_editing)
):
    """Releases a pessimistic lock on an artifact."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    try:
        await ArtifactLockManager.release_lock(db, id, holder_id)
        return {"status": "unlocked"}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/admin/agents/artifacts/{id}/review", response_model=ArtifactReviewRead)
async def review_artifact(
    id: uuid.UUID,
    payload: ArtifactReviewCreate,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_artifacts)
):
    """Adds a review/approval to an artifact and promotions it to 'published' status if approved."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    try:
        review = await ArtifactReviewManager.add_review(
            db=db,
            artifact_id=id,
            version_id=payload.version_id,
            reviewer_id=payload.reviewer_id,
            reviewer_type=payload.reviewer_type,
            status=payload.status,
            comment=payload.comment
        )

        # If review is approved, we can trigger promotion to published status automatically
        if payload.status == "approved" and artifact.current_version_id == payload.version_id:
            await ArtifactReviewManager.promote_artifact(db, artifact, payload.reviewer_id, payload.reviewer_type)

        return review
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/admin/agents/artifacts/{id}/comments", response_model=ArtifactCommentRead)
async def add_artifact_comment(
    id: uuid.UUID,
    payload: ArtifactCommentCreate,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_artifacts)
):
    """Posts a comment on an artifact."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    comment = await ArtifactReviewManager.add_comment(
        db=db,
        artifact_id=id,
        author_id=payload.author_id,
        author_type=payload.author_type,
        content=payload.content,
        version_id=payload.version_id,
        parent_id=payload.parent_id
    )
    return comment


@router.get("/admin/agents/artifacts/{id}/export")
async def export_artifact_sanitized(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_artifacts)
):
    """Exports the artifact content with sensitive information sanitized."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    if not artifact.current_version_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Artifact has no versions to export.")

    # Get current version
    stmt = select(AgentArtifactVersion).where(AgentArtifactVersion.id == artifact.current_version_id)
    res = await db.execute(stmt)
    version = res.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current version not found.")

    sanitized_content = ArtifactVersioningManager.sanitize_content(version.content, artifact.artifact_type)
    return {
        "id": str(artifact.id),
        "name": artifact.name,
        "artifact_type": artifact.artifact_type,
        "version_number": version.version_number,
        "content": sanitized_content
    }


@router.get("/admin/agents/artifacts/{id}/events", response_model=List[ArtifactEventRead])
async def get_artifact_events(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_artifacts)
):
    """Lists the event trail of an artifact (provenance timeline)."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    stmt = select(AgentArtifactEvent).where(AgentArtifactEvent.artifact_id == id).order_by(AgentArtifactEvent.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/admin/agents/artifacts/{id}/versions", response_model=List[ArtifactVersionRead])
async def list_artifact_versions(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff = Depends(require_shared_artifacts)
):
    """Lists all versions of an artifact, enforcing tenant isolation."""
    artifact = await SharedArtifactRegistry.get_artifact(db, id, tenant_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    stmt = select(AgentArtifactVersion).where(AgentArtifactVersion.artifact_id == id).order_by(AgentArtifactVersion.version_number.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/admin/agents/workspaces/{id}/artifacts", response_model=List[ArtifactRead])
async def list_workspace_artifacts(
    id: uuid.UUID,
    tenant_id: str = "default",
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_admin_token),
    _ff_ws = Depends(require_shared_workspace),
    _ff_art = Depends(require_shared_artifacts)
):
    """Lists all artifacts in a workspace, enforcing tenant isolation."""
    artifacts = await SharedArtifactRegistry.list_artifacts(db, id, tenant_id)
    return artifacts
