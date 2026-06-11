from __future__ import annotations

import uuid
from datetime import datetime, UTC, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from app.core.config import get_settings
from app.models.agents.agents import AgentDefinition
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.models.operations.disaster_recovery import RestoreRequest

@pytest.fixture(autouse=True)
def setup_backup_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)

@pytest.mark.asyncio
async def test_backup_restore_approval_workflow(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(repo_root))
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "config").mkdir(parents=True, exist_ok=True)
    (repo_root / "VERSION").write_text("1.0.0", encoding="utf-8")
    
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")
    settings.backup_restore_enabled = True
    settings.deployment_mode = "appliance"

    # Seed some data to make backup work
    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with session_local() as session:
        agent = AgentDefinition(
            id=uuid.uuid4(),
            name="Strong Approval Agent",
            version="1.0.0",
            instructions="Serve database backup test.",
            model_id="mock-model",
            owner="db-test",
            tenant_id="tenant-db",
            status="active"
        )
        session.add(agent)
        await session.commit()

    # 1. Create a backup
    create_response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    assert create_response.status_code == 200
    backup_id = create_response.json()["backup_id"]

    # 2. Create restore request
    req_payload = {"backup_id": backup_id, "dry_run": True}
    create_req_res = await admin_client.post(
        "/admin/backup/restore-requests",
        headers=admin_token_headers,
        json=req_payload
    )
    assert create_req_res.status_code == 200
    req_data = create_req_res.json()
    assert req_data["status"] == "pending"
    assert req_data["backup_id"] == backup_id
    assert req_data["dry_run"] is True
    req_id = req_data["id"]

    # 3. Test self-approval blocking in production mode
    # Set deployment mode to production
    settings.deployment_mode = "production"
    
    approve_res = await admin_client.post(
        f"/admin/backup/restore-requests/{req_id}/approve",
        headers=admin_token_headers
    )
    # Self-approval by same user should be blocked
    assert approve_res.status_code == 400
    assert "Self-approval is blocked" in approve_res.json()["detail"]

    # 4. Test approval in non-production mode
    settings.deployment_mode = "appliance"
    approve_res = await admin_client.post(
        f"/admin/backup/restore-requests/{req_id}/approve",
        headers=admin_token_headers
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()
    assert approved_data["status"] == "approved"
    assert approved_data["token"] is not None
    token = approved_data["token"]

    # 5. Test execution with invalid token
    exec_res_invalid = await admin_client.post(
        f"/admin/backup/restore-requests/{req_id}/execute",
        headers=admin_token_headers,
        json={"token": "invalid-token"}
    )
    assert exec_res_invalid.status_code == 400

    # 6. Test successful execution
    exec_res_valid = await admin_client.post(
        f"/admin/backup/restore-requests/{req_id}/execute",
        headers=admin_token_headers,
        json={"token": token}
    )
    assert exec_res_valid.status_code == 200
    assert exec_res_valid.json()["status"] == "dry_run_complete"

    # 7. Test expired token validation
    # Create another request
    create_req_res2 = await admin_client.post(
        "/admin/backup/restore-requests",
        headers=admin_token_headers,
        json={"backup_id": backup_id, "dry_run": True}
    )
    req_id2 = create_req_res2.json()["id"]

    # Manually modify expiration date in database to the past
    async with session_local() as session:
        res = await session.execute(select(RestoreRequest).where(RestoreRequest.id == req_id2))
        db_req = res.scalar_one()
        db_req.expires_at = datetime.now(UTC) - timedelta(minutes=5)
        await session.commit()

    # Try to approve expired request
    approve_expired = await admin_client.post(
        f"/admin/backup/restore-requests/{req_id2}/approve",
        headers=admin_token_headers
    )
    assert approve_expired.status_code == 400
    assert "expired" in approve_expired.json()["detail"]

    # Verify status in database changed to expired
    async with session_local() as session:
        res = await session.execute(select(RestoreRequest).where(RestoreRequest.id == req_id2))
        db_req = res.scalar_one()
        assert db_req.status == "expired"

    await engine.dispose()
