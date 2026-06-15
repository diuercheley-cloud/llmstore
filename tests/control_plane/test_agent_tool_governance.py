import uuid
from pathlib import Path

import app.db.session
import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.agents import tool_registry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force SQLite for tests
TEST_DB_FILE = Path("/tmp/test-tool-governance.db")


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
        except:
            pass


@pytest.mark.asyncio
async def test_tool_registration_missing_risk_fails(test_db):
    async with test_db() as db:
        data = {
            "name": "test_tool",
            "category": "retrieval",
            "input_schema_json": {"type": "object"},
            "output_schema_json": {"type": "object"},
            "timeout_seconds": 30,
            # risk_level missing
        }
        with pytest.raises(ValueError, match="risk_level"):
            await tool_registry.create_tool(db, data)


@pytest.mark.asyncio
async def test_tool_registration_missing_timeout_fails(test_db):
    async with test_db() as db:
        data = {
            "name": "test_tool",
            "category": "retrieval",
            "input_schema_json": {"type": "object"},
            "output_schema_json": {"type": "object"},
            "risk_level": "low",
            # timeout missing
        }
        with pytest.raises(ValueError, match="timeout_seconds"):
            await tool_registry.create_tool(db, data)


@pytest.mark.asyncio
async def test_destructive_tool_requires_approval_policy(test_db):
    async with test_db() as db:
        data = {
            "name": "wipe_db",
            "category": "admin_operation",
            "input_schema_json": {"type": "object"},
            "output_schema_json": {"type": "object"},
            "risk_level": "critical",
            "side_effect_level": "destructive",
            "timeout_seconds": 60,
            # approval_policy missing
        }
        with pytest.raises(ValueError, match="approval_policy"):
            await tool_registry.create_tool(db, data)


@pytest.mark.asyncio
async def test_external_tool_requires_data_boundary(test_db):
    async with test_db() as db:
        data = {
            "name": "google_search",
            "category": "external_api",
            "input_schema_json": {"type": "object"},
            "output_schema_json": {"type": "object"},
            "risk_level": "medium",
            "side_effect_level": "external",
            "timeout_seconds": 10,
            # data_boundary missing
        }
        with pytest.raises(ValueError, match="data_boundary"):
            await tool_registry.create_tool(db, data)


@pytest.mark.asyncio
async def test_tool_exceeds_max_calls_per_run(test_db):
    async with test_db() as db:
        data = {
            "name": "limited_tool",
            "category": "retrieval",
            "input_schema_json": {"type": "object"},
            "output_schema_json": {"type": "object"},
            "risk_level": "low",
            "timeout_seconds": 5,
            "max_calls_per_run": 1,
        }
        tool = await tool_registry.create_tool(db, data)
        run_id = uuid.uuid4()

        from app.core.config import get_settings
        from app.services.agents import tool_executor

        settings = get_settings()
        settings.agent_execution_enabled = True
        settings.agent_tool_execution_enabled = True

        # First call: Success
        await tool_executor.execute_tool(db, tool, {}, run_id=run_id)

        # Second call: Fails
        with pytest.raises(ValueError, match="exceeded max_calls_per_run"):
            await tool_executor.execute_tool(db, tool, {}, run_id=run_id)


@pytest.mark.asyncio
async def test_retry_on_non_idempotent_tool_blocked(test_db):
    async with test_db() as db:
        data = {
            "name": "write_tool",
            "category": "database_write",
            "input_schema_json": {"type": "object"},
            "output_schema_json": {"type": "object"},
            "risk_level": "medium",
            "side_effect_level": "write",
            "timeout_seconds": 5,
            "approval_policy": {"type": "auto"},
            "retry_policy": {"max_attempts": 3},
            "enabled": True,
        }
        tool = await tool_registry.create_tool(db, data)

        from app.services.agents import tool_executor

        call_count = 0

        async def failing_tool(**kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Failure")

        with pytest.raises(RuntimeError):
            await tool_executor.execute_tool(
                db, tool, {}, tool_callable=failing_tool, executed_by="admin"
            )

        # Should NOT retry because it's 'write'
        assert call_count == 1


@pytest.mark.asyncio
async def test_retry_on_idempotent_tool_works(test_db):
    async with test_db() as db:
        data = {
            "name": "read_tool",
            "category": "retrieval",
            "input_schema_json": {"type": "object"},
            "output_schema_json": {"type": "object"},
            "risk_level": "low",
            "side_effect_level": "read",
            "timeout_seconds": 5,
            "retry_policy": {"max_attempts": 2, "initial_backoff": 0.1},
            "enabled": True,
        }
        tool = await tool_registry.create_tool(db, data)

        from app.services.agents import tool_executor

        call_count = 0

        async def failing_then_success(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Temporary Failure")
            return {"result": "ok"}

        result = await tool_executor.execute_tool(db, tool, {}, tool_callable=failing_then_success)

        assert call_count == 2
        assert result["result"] == "ok"
