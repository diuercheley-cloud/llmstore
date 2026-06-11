from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.services.backup.restore_lock_service import RestoreLockService
from app.models.agents.agent_workflows import AgentWorkflowDefinition, AgentWorkflowEdge, AgentWorkflowNode
from app.models.agents.agents import AgentDefinition, AgentMemoryIndex, AgentMemoryItem, AgentRegistryEntry, AgentVersion
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

@pytest.fixture(autouse=True)
def setup_backup_keys(monkeypatch):
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "a" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "b" * 32)


async def _seed_backup_data(session: AsyncSession) -> dict[str, str]:
    agent_id = uuid.uuid4()
    registry_id = uuid.uuid4()
    workflow_id = uuid.uuid4()
    memory_item_id = uuid.uuid4()
    memory_index_id = uuid.uuid4()

    agent = AgentDefinition(
        id=agent_id,
        name="Ops Agent",
        version="1.0.0",
        instructions="Handle platform operations.",
        model_id="mock-model",
        owner="platform",
        tenant_id="tenant-a",
        status="active",
    )
    registry = AgentRegistryEntry(
        id=registry_id,
        agent_id=agent_id,
        name="Ops Agent",
        semantic_version="1.0.0",
        status="active",
    )
    version = AgentVersion(
        agent_registry_id=registry_id,
        semantic_version="1.0.0",
        instructions="Handle platform operations.",
    )
    workflow = AgentWorkflowDefinition(
        id=workflow_id,
        tenant_id="tenant-a",
        name="restore-flow",
        version="1.0.0",
        input_schema={},
        output_schema={},
        metadata_json={"category": "dr"},
    )
    node = AgentWorkflowNode(
        workflow_definition_id=workflow_id,
        node_key="start",
        node_type="task",
        config={"action": "backup"},
        metadata_json={},
    )
    edge = AgentWorkflowEdge(
        workflow_definition_id=workflow_id,
        from_node_key="start",
        to_node_key="start",
        metadata_json={},
    )
    memory_item = AgentMemoryItem(
        id=memory_item_id,
        tenant_id="tenant-a",
        agent_id=agent_id,
        collection_id=None,
        memory_type="vector",
        content_hash="hash-1",
        raw_content="critical memory",
        provenance={"source": "unit-test"},
        retention_until=datetime.now(UTC) + timedelta(days=30),
    )
    memory_index = AgentMemoryIndex(
        id=memory_index_id,
        tenant_id="tenant-a",
        agent_id=agent_id,
        memory_item_id=memory_item_id,
        index_status="completed",
        vector_id="vec-1",
        embedding="[0.1,0.2,0.3]",
    )

    session.add_all([agent, registry, version, workflow, node, edge, memory_item, memory_index])
    await session.commit()
    return {
        "agent_id": str(agent_id),
        "workflow_id": str(workflow_id),
        "memory_index_id": str(memory_index_id),
    }


def _prepare_config_tree(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / ".env").write_text("ADMIN_TOKEN=test-token\nFEATURE_A=true\n", encoding="utf-8")
    (root / ".env.local").write_text("LOCAL_ONLY=yes\n", encoding="utf-8")
    (root / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    (root / "config" / "feature-flags.yaml").write_text("flags:\n  demo_enabled: true\n", encoding="utf-8")
    (root / "config" / "app.yaml").write_text("profile: appliance\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_backup_create_and_verify(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    _prepare_config_tree(tmp_path / "repo")
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        await _seed_backup_data(session)

    response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "full"
    assert payload["auto_verification_status"] == "valid"
    assert {component["name"] for component in payload["components"]} == {
        "database",
        "configs",
        "feature_flags",
        "agents",
        "workflows",
        "embeddings_metadata",
    }

    verify = await admin_client.post(f"/admin/backup/{payload['backup_id']}/verify", headers=admin_token_headers)
    assert verify.status_code == 200
    verify_payload = verify.json()
    assert verify_payload["status"] == "valid"
    assert verify_payload["signature_valid"] is True
    assert verify_payload["archive_checksum_valid"] is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_restore_recovers_data_and_files(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(repo_root))
    _prepare_config_tree(repo_root)
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")
    settings.backup_restore_enabled = True

    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        seeded = await _seed_backup_data(session)

    create_response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    backup_id = create_response.json()["backup_id"]

    async with session_local() as session:
        agent = await session.get(AgentDefinition, uuid.UUID(seeded["agent_id"]))
        agent.name = "Mutated Agent"
        workflow = await session.get(AgentWorkflowDefinition, uuid.UUID(seeded["workflow_id"]))
        workflow.name = "mutated-flow"
        memory_index = await session.get(AgentMemoryIndex, uuid.UUID(seeded["memory_index_id"]))
        memory_index.vector_id = "vec-mutated"
        await session.commit()

    (repo_root / ".env").write_text("ADMIN_TOKEN=mutated\n", encoding="utf-8")
    (repo_root / "config" / "feature-flags.yaml").write_text("flags:\n  demo_enabled: false\n", encoding="utf-8")

    restore_response = await admin_client.post(
        f"/admin/backup/{backup_id}/restore",
        headers=admin_token_headers,
        json={"dry_run": False},
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["status"] == "restored"

    async with session_local() as session:
        agent = await session.get(AgentDefinition, uuid.UUID(seeded["agent_id"]))
        workflow = await session.get(AgentWorkflowDefinition, uuid.UUID(seeded["workflow_id"]))
        memory_index = await session.get(AgentMemoryIndex, uuid.UUID(seeded["memory_index_id"]))
        assert agent.name == "Ops Agent"
        assert workflow.name == "restore-flow"
        assert memory_index.vector_id == "vec-1"

    # Under the new security defaults, .env is not included in the backup,
    # so it remains in its mutated state post-restore
    assert "ADMIN_TOKEN=mutated" in (repo_root / ".env").read_text(encoding="utf-8")
    assert "demo_enabled: true" in (repo_root / "config" / "feature-flags.yaml").read_text(encoding="utf-8")

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_status_reports_integrity(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    _prepare_config_tree(tmp_path / "repo")
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        await _seed_backup_data(session)

    create_response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    backup_id = create_response.json()["backup_id"]

    status_response = await admin_client.get(f"/admin/backup/{backup_id}/status", headers=admin_token_headers)
    assert status_response.status_code == 200
    assert status_response.json()["integrity"] == "valid"

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_detects_corruption_and_blocks_restore(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    _prepare_config_tree(tmp_path / "repo")
    settings = get_settings()
    backup_store = tmp_path / "backup-store"
    settings.disaster_recovery_backup_dir = str(backup_store)
    settings.backup_restore_enabled = True

    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        await _seed_backup_data(session)

    create_response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    backup_id = create_response.json()["backup_id"]

    payload_path = backup_store / "system" / backup_id / "payload.tar.gz.enc"
    payload = bytearray(payload_path.read_bytes())
    payload[10] = (payload[10] + 1) % 255
    payload_path.write_bytes(bytes(payload))

    verify_response = await admin_client.post(f"/admin/backup/{backup_id}/verify", headers=admin_token_headers)
    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "corrupted"

    restore_response = await admin_client.post(
        f"/admin/backup/{backup_id}/restore",
        headers=admin_token_headers,
        json={"dry_run": False},
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["status"] == "blocked"

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_restore_disabled_by_default(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    _prepare_config_tree(tmp_path / "repo")
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")
    settings.backup_restore_enabled = False

    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        await _seed_backup_data(session)

    create_response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    backup_id = create_response.json()["backup_id"]

    dry_run_response = await admin_client.post(
        f"/admin/backup/{backup_id}/restore/dry-run",
        headers=admin_token_headers,
    )
    assert dry_run_response.status_code != 403

    restore_response = await admin_client.post(
        f"/admin/backup/{backup_id}/restore",
        headers=admin_token_headers,
        json={"dry_run": False},
    )
    assert restore_response.status_code == 403
    assert "Restore real está desabilitado por segurança" in restore_response.json()["detail"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_verify_returns_manifest_error_code(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    _prepare_config_tree(tmp_path / "repo")
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        await _seed_backup_data(session)

    create_response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    backup_id = create_response.json()["backup_id"]

    manifest_path = tmp_path / "backup-store" / "system" / backup_id / "manifest.json"
    manifest_path.write_text("{invalid-json", encoding="utf-8")

    verify_response = await admin_client.post(f"/admin/backup/{backup_id}/verify", headers=admin_token_headers)
    assert verify_response.status_code == 400
    payload = verify_response.json()
    assert payload["error"]["code"] == "BACKUP_MANIFEST_INVALID"
    assert payload["error"]["message"]
    assert payload["correlation_id"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_verify_returns_key_missing_code(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    _prepare_config_tree(tmp_path / "repo")
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")

    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        await _seed_backup_data(session)

    create_response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    backup_id = create_response.json()["backup_id"]

    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "x" * 32)
    monkeypatch.setenv("BACKUP_SIGNING_KEY", "y" * 32)

    verify_response = await admin_client.post(f"/admin/backup/{backup_id}/verify", headers=admin_token_headers)
    assert verify_response.status_code == 200
    payload = verify_response.json()
    assert payload["status"] == "corrupted"
    assert payload["error_code"] == "BACKUP_KEY_MISSING"

    await engine.dispose()


@pytest.mark.asyncio
async def test_backup_restore_returns_lock_error_code(admin_client, admin_token_headers, isolated_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("LLMSTACK_BACKUP_SOURCE_ROOT", str(tmp_path / "repo"))
    _prepare_config_tree(tmp_path / "repo")
    settings = get_settings()
    settings.disaster_recovery_backup_dir = str(tmp_path / "backup-store")
    settings.backup_restore_enabled = True

    engine = create_async_engine(isolated_db_url)
    session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_local() as session:
        await _seed_backup_data(session)

    create_response = await admin_client.post("/admin/backup", headers=admin_token_headers, json={"full": True})
    backup_id = create_response.json()["backup_id"]

    async def deny_lock(self):
        return False

    monkeypatch.setattr(RestoreLockService, "acquire_lock", deny_lock)

    restore_response = await admin_client.post(
        f"/admin/backup/{backup_id}/restore",
        headers=admin_token_headers,
        json={"dry_run": False},
    )
    assert restore_response.status_code == 423
    payload = restore_response.json()
    assert payload["error"]["code"] == "RESTORE_LOCKED"
    assert payload["error"]["details"]["backup_id"] == backup_id

    await engine.dispose()
