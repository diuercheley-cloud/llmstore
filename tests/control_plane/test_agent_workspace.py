import uuid

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agent_workspace import AgentArtifactVersion
from app.services.agents.workspace import (
    ArtifactDiffManager,
    ArtifactLockManager,
    ArtifactReviewManager,
    ArtifactVersioningManager,
    SharedArtifactRegistry,
)
from sqlalchemy.future import select


@pytest.fixture(autouse=True)
def enable_feature_flags():
    settings = get_settings()
    old_ws = settings.agent_shared_workspace_enabled
    old_art = settings.agent_shared_artifacts_enabled
    old_edit = settings.agent_collaborative_editing_enabled

    settings.agent_shared_workspace_enabled = True
    settings.agent_shared_artifacts_enabled = True
    settings.agent_collaborative_editing_enabled = True
    yield
    settings.agent_shared_workspace_enabled = old_ws
    settings.agent_shared_artifacts_enabled = old_art
    settings.agent_collaborative_editing_enabled = old_edit


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_workspace_creation_and_listing(db_session):
    ws = await SharedArtifactRegistry.create_workspace(
        db=db_session,
        name="Team Workspace",
        tenant_id="tenant-a",
        owner_id="human-1",
        description="Workspace for project a"
    )
    assert ws.id is not None
    assert ws.name == "Team Workspace"
    assert ws.tenant_id == "tenant-a"

    # List workspaces
    workspaces = await SharedArtifactRegistry.list_workspaces(db_session, "tenant-a")
    assert len(workspaces) == 1
    assert workspaces[0].id == ws.id

    # Tenant isolation list
    empty = await SharedArtifactRegistry.list_workspaces(db_session, "tenant-b")
    assert len(empty) == 0


@pytest.mark.asyncio
async def test_artifact_immutable_versioning_and_provenance(db_session):
    ws = await SharedArtifactRegistry.create_workspace(db_session, "WS1", "tenant-a", "human-1")
    
    # 1. Create artifact with initial version (Provenance check: Agent registers run_id, step_id)
    run_id = uuid.uuid4()
    step_id = uuid.uuid4()
    artifact = await SharedArtifactRegistry.create_artifact(
        db=db_session,
        workspace_id=ws.id,
        tenant_id="tenant-a",
        owner_id="agent-1",
        name="Baseline Prompt",
        artifact_type="prompt_baseline",
        content="Hello world instruction",
        creator_id="agent-1",
        creator_type="agent",
        run_id=run_id,
        step_id=step_id,
        change_summary="Initial commit"
    )
    
    assert artifact.id is not None
    assert artifact.status == "draft"
    
    # Check initial version
    stmt = select(AgentArtifactVersion).where(AgentArtifactVersion.artifact_id == artifact.id)
    res = await db_session.execute(stmt)
    versions = res.scalars().all()
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].content == "Hello world instruction"
    assert versions[0].creator_type == "agent"
    assert versions[0].run_id == run_id
    assert versions[0].step_id == step_id

    # 2. Immutable version update
    version2 = await ArtifactVersioningManager.create_version(
        db=db_session,
        artifact=artifact,
        content="Updated instruction",
        creator_id="human-2",
        creator_type="human",
        change_summary="Refining instruction"
    )
    assert version2.version_number == 2
    assert version2.content == "Updated instruction"

    # Verify old version content remains untouched (immutability)
    db_session.expire_all()
    res = await db_session.execute(stmt.order_by(AgentArtifactVersion.version_number.asc()))
    all_versions = res.scalars().all()
    assert len(all_versions) == 2
    assert all_versions[0].content == "Hello world instruction"
    assert all_versions[1].content == "Updated instruction"


@pytest.mark.asyncio
async def test_concurrency_locks(db_session):
    ws = await SharedArtifactRegistry.create_workspace(db_session, "WS1", "tenant-a", "human-1")
    artifact = await SharedArtifactRegistry.create_artifact(
        db=db_session, workspace_id=ws.id, tenant_id="tenant-a", owner_id="human-1",
        name="Code File", artifact_type="code_file", content="print('hello')",
        creator_id="human-1", creator_type="human"
    )

    # 1. Pessimistic Lock
    # human-1 locks the artifact
    lock = await ArtifactLockManager.acquire_lock(db_session, artifact.id, "human-1", "human")
    assert lock.holder_id == "human-1"

    # Try to acquire lock by human-2 (fails)
    with pytest.raises(PermissionError):
        await ArtifactLockManager.acquire_lock(db_session, artifact.id, "human-2", "human")

    # Try to edit by human-2 (fails)
    with pytest.raises(PermissionError):
        await ArtifactLockManager.check_write_allowed(db_session, artifact.id, "human-2")

    # Edit by lock holder human-1 (succeeds)
    await ArtifactLockManager.check_write_allowed(db_session, artifact.id, "human-1")
    
    # Release lock
    await ArtifactLockManager.release_lock(db_session, artifact.id, "human-1")

    # 2. Optimistic Lock
    # Succeeds if we provide current version ID
    ArtifactLockManager.verify_optimistic_lock(artifact, expected_version_id=artifact.current_version_id)
    
    # Fails if we provide a random mismatching version ID
    with pytest.raises(ValueError):
        ArtifactLockManager.verify_optimistic_lock(artifact, expected_version_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_diff_generation(db_session):
    ws = await SharedArtifactRegistry.create_workspace(db_session, "WS1", "tenant-a", "human-1")
    artifact = await SharedArtifactRegistry.create_artifact(
        db=db_session, workspace_id=ws.id, tenant_id="tenant-a", owner_id="human-1",
        name="Doc", artifact_type="markdown_doc", content="Line 1\nLine 2",
        creator_id="human-1", creator_type="human"
    )
    v1 = await ArtifactDiffManager.get_version_by_number(db_session, artifact.id, 1)

    await ArtifactVersioningManager.create_version(
        db=db_session, artifact=artifact, content="Line 1\nLine 2 modified\nLine 3",
        creator_id="human-1", creator_type="human"
    )
    v2 = await ArtifactDiffManager.get_version_by_number(db_session, artifact.id, 2)

    diff_res = ArtifactDiffManager.compute_diff(v1.content, v2.content)
    assert "Line 2 modified" in diff_res["raw_diff"]
    
    structured = diff_res["structured"]
    assert any(line["type"] == "delete" and "Line 2" in line["value"] for line in structured)
    assert any(line["type"] == "insert" and "Line 2 modified" in line["value"] for line in structured)
    assert any(line["type"] == "insert" and "Line 3" in line["value"] for line in structured)


@pytest.mark.asyncio
async def test_reviews_approvals_and_promotion(db_session):
    ws = await SharedArtifactRegistry.create_workspace(db_session, "WS1", "tenant-a", "human-1")
    artifact = await SharedArtifactRegistry.create_artifact(
        db=db_session, workspace_id=ws.id, tenant_id="tenant-a", owner_id="human-1",
        name="Doc", artifact_type="markdown_doc", content="Draft content",
        creator_id="human-1", creator_type="human"
    )

    # 1. Verify promotion fails without approval
    with pytest.raises(PermissionError):
        await ArtifactReviewManager.promote_artifact(db_session, artifact, "human-2", "human")

    # 2. Add rejection review
    await ArtifactReviewManager.add_review(
        db=db_session, artifact_id=artifact.id, version_id=artifact.current_version_id,
        reviewer_id="human-2", reviewer_type="human", status="rejected", comment="Not good enough"
    )
    with pytest.raises(PermissionError):
        await ArtifactReviewManager.promote_artifact(db_session, artifact, "human-2", "human")

    # 3. Add approved review and promote
    await ArtifactReviewManager.add_review(
        db=db_session, artifact_id=artifact.id, version_id=artifact.current_version_id,
        reviewer_id="human-3", reviewer_type="human", status="approved", comment="Looks great!"
    )
    await ArtifactReviewManager.promote_artifact(db_session, artifact, "human-3", "human")
    assert artifact.status == "published"


@pytest.mark.asyncio
async def test_tenant_isolation(db_session):
    ws = await SharedArtifactRegistry.create_workspace(db_session, "WS1", "tenant-a", "human-1")
    artifact = await SharedArtifactRegistry.create_artifact(
        db=db_session, workspace_id=ws.id, tenant_id="tenant-a", owner_id="human-1",
        name="Doc", artifact_type="markdown_doc", content="Sensitive text",
        creator_id="human-1", creator_type="human"
    )

    # Attempt cross-tenant get artifact (fails)
    with pytest.raises(PermissionError):
        await SharedArtifactRegistry.get_artifact(db_session, artifact.id, tenant_id="tenant-b")

    # Access under correct tenant (succeeds)
    fetched = await SharedArtifactRegistry.get_artifact(db_session, artifact.id, tenant_id="tenant-a")
    assert fetched is not None


@pytest.mark.asyncio
async def test_export_content_sanitization(db_session):
    content = "My OpenAI API Key: sk-local-example-1234567890\nAlso secret token: \"api_key\": \"sec_token_val_123\""
    sanitized = ArtifactVersioningManager.sanitize_content(content, "workflow_definition")
    
    assert "sk-local-example-1234567890" not in sanitized
    assert "sec_token_val_123" not in sanitized
    assert "REDACTED" in sanitized


@pytest.mark.asyncio
async def test_api_endpoints_integration(async_client, admin_token_headers):
    # 1. Create Workspace
    resp = await async_client.post(
        "/admin/agents/workspaces",
        json={"name": "Integration WS", "description": "integration testing"},
        headers=admin_token_headers
    )
    assert resp.status_code == 201
    ws_data = resp.json()
    ws_id = ws_data["id"]

    # 2. List Workspaces
    resp = await async_client.get("/admin/agents/workspaces", headers=admin_token_headers)
    assert resp.status_code == 200
    assert any(w["id"] == ws_id for w in resp.json())

    # 3. Create Artifact
    resp = await async_client.post(
        f"/admin/agents/workspaces/{ws_id}/artifacts",
        json={
            "name": "API Tool",
            "artifact_type": "tool_definition",
            "content": "def run():\n  api_key = 'sk-12345'",
            "creator_id": "human-1",
            "creator_type": "human"
        },
        headers=admin_token_headers
    )
    assert resp.status_code == 201
    art_data = resp.json()
    art_id = art_data["id"]

    # 4. Lock Artifact
    resp = await async_client.post(
        f"/admin/agents/artifacts/{art_id}/lock",
        json={"holder_id": "human-1", "holder_type": "human"},
        headers=admin_token_headers
    )
    assert resp.status_code == 200
    assert resp.json()["holder_id"] == "human-1"

    # 5. Lock prevents edits from human-2
    resp = await async_client.post(
        f"/admin/agents/artifacts/{art_id}/versions",
        json={
            "content": "changed content",
            "creator_id": "human-2",
            "creator_type": "human"
        },
        headers=admin_token_headers
    )
    assert resp.status_code == 409

    # 6. Unlock
    resp = await async_client.post(
        f"/admin/agents/artifacts/{art_id}/unlock?holder_id=human-1",
        headers=admin_token_headers
    )
    assert resp.status_code == 200

    # 7. Add Comment
    resp = await async_client.post(
        f"/admin/agents/artifacts/{art_id}/comments",
        json={
            "content": "First comment",
            "author_id": "human-1",
            "author_type": "human"
        },
        headers=admin_token_headers
    )
    assert resp.status_code == 200

    # 8. Export sanitized content
    resp = await async_client.get(
        f"/admin/agents/artifacts/{art_id}/export",
        headers=admin_token_headers
    )
    assert resp.status_code == 200
    export_data = resp.json()
    assert "sk-12345" not in export_data["content"]
    assert "REDACTED" in export_data["content"]
