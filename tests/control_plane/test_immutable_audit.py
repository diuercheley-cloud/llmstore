import json
from pathlib import Path

import app.db.session
import httpx
import pytest
import pytest_asyncio
from app.db.base import Base
from app.main import app as fastapi_app
from app.models.agents.immutable_audit import ImmutableAuditLog
from app.services.security.immutable_audit import ImmutableAuditStore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_FILE = Path("/tmp/test-immutable-audit.db")


@pytest_asyncio.fixture(autouse=True)
async def test_db():
    db_url = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    app.db.session.engine = engine
    app.db.session.SessionLocal = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield session_factory

    await engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_immutable_audit_store_hashing_and_signing(test_db):
    session_factory = test_db
    async with session_factory() as db:
        # Write first block (genesis)
        entry1 = await ImmutableAuditStore.write_entry(
            db=db,
            action="create_agent",
            actor="admin@company.com",
            payload={"name": "Assistant", "model": "gpt-4"},
            tenant_id="t1",
        )
        assert entry1.previous_hash is None
        assert entry1.hash is not None
        assert entry1.signature is not None

        # Write second block (chained)
        entry2 = await ImmutableAuditStore.write_entry(
            db=db,
            action="update_policy",
            actor="ops@company.com",
            payload={"policy_id": "policy-01", "rules": ["no_shell"]},
            tenant_id="t1",
        )
        assert entry2.previous_hash == entry1.hash
        assert entry2.hash is not None

        # Verify chain integrity
        is_valid, failed_id, reason = await ImmutableAuditStore.verify_chain(db)
        assert is_valid is True, f"Verify failed at block {failed_id}: {reason}"
        assert failed_id is None
        assert reason is None

        # Export verification
        exported = await ImmutableAuditStore.export_logs(db)
        assert len(exported) == 2
        assert exported[0]["action"] == "create_agent"
        assert exported[1]["previous_hash"] == exported[0]["hash"]


@pytest.mark.asyncio
async def test_immutable_audit_store_tamper_detection(test_db):
    session_factory = test_db
    async with session_factory() as db:
        # Write three blocks
        await ImmutableAuditStore.write_entry(db, "act1", "user", {"k": 1}, "t1")
        entry2 = await ImmutableAuditStore.write_entry(db, "act2", "user", {"k": 2}, "t1")
        await ImmutableAuditStore.write_entry(db, "act3", "user", {"k": 3}, "t1")

        # Confirm valid initially
        is_valid, failed_id, reason = await ImmutableAuditStore.verify_chain(db)
        assert is_valid is True, f"Verify failed at block {failed_id}: {reason}"

        # Tamper with the second block by changing its payload manually in DB
        entry2.payload = json.dumps({"k": 999}, sort_keys=True)
        db.add(entry2)
        await db.commit()

        # Run verification and assert failure
        is_valid, failed_id, reason = await ImmutableAuditStore.verify_chain(db)
        assert is_valid is False
        assert failed_id == entry2.id
        assert "Hash mismatch" in reason


@pytest.mark.asyncio
async def test_api_audit_verify_endpoint(test_db):
    session_factory = test_db

    # Pre-populate some logs
    async with session_factory() as db:
        await ImmutableAuditStore.write_entry(db, "action_a", "system", {"status": "ok"}, "t1")
        await ImmutableAuditStore.write_entry(db, "action_b", "system", {"status": "error"}, "t1")

    # Use HTTP client to test verify endpoint
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app), base_url="http://test"
    ) as client:
        # Test verify
        response = await client.post("/api/audit/verify")
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["status"] == "success"

        # Test export
        export_resp = await client.get("/api/audit/export")
        assert export_resp.status_code == 200
        logs = export_resp.json()
        assert len(logs) == 2
        assert logs[0]["action"] == "action_a"

        # Tamper with database block
        async with session_factory() as db:
            stmt = select(ImmutableAuditLog).order_by(ImmutableAuditLog.id.desc()).limit(1)
            res = await db.execute(stmt)
            last = res.scalar_one()
            last.action = "tampered_action"
            db.add(last)
            await db.commit()
            last_id = last.id

        # Verify again via API and confirm failure detection
        fail_response = await client.post("/api/audit/verify")
        assert fail_response.status_code == 200
        fail_data = fail_response.json()
        assert fail_data["is_valid"] is False
        assert fail_data["status"] == "failed"
        assert fail_data["failed_block_id"] == last_id
