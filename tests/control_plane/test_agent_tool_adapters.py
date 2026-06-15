import uuid

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agents import AgentTool
from app.services.agents.tool_adapter_registry import adapter_registry
from app.services.agents.tool_adapters import register_all_adapters
from app.services.agents.tool_executor import execute_tool
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents.agents  # noqa
        import app.models.agents.agent_tool_execution  # noqa

        await conn.run_sync(Base.metadata.create_all)

    # Initialize adapters for testing
    register_all_adapters()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    adapter_registry.clear()


@pytest.mark.asyncio
async def test_adapter_registration():
    # adapters should be registered by the fixture
    adapters = adapter_registry.list_adapters()
    assert len(adapters) >= 8

    echo = adapter_registry.get_adapter("echo_tool")
    assert echo is not None
    assert echo.version == "1.0.0"
    assert "message" in echo.input_schema["properties"]


@pytest.mark.asyncio
async def test_adapter_execution_echo(db_session: AsyncSession):
    settings = get_settings()
    settings.agent_tool_adapters_enabled = True
    settings.agent_tool_execution_enabled = True

    tool = AgentTool(
        id=uuid.uuid4(),
        name="echo_tool",
        version="1.0.0",
        category="filesystem_safe",
        input_schema_json={"type": "object", "properties": {"message": {"type": "string"}}},
        output_schema_json={"type": "object", "properties": {"echo": {"type": "string"}}},
        side_effect_level="none",
        timeout_seconds=5,
    )
    db_session.add(tool)
    await db_session.commit()

    output = await execute_tool(db=db_session, tool=tool, parameters={"message": "hello world"})

    assert output["echo"] == "hello world"


@pytest.mark.asyncio
async def test_adapter_dry_run_http(db_session: AsyncSession):
    settings = get_settings()
    settings.agent_tool_adapters_enabled = True
    settings.agent_tool_execution_enabled = True

    tool = AgentTool(
        id=uuid.uuid4(),
        name="http_get_tool",
        version="1.0.0",
        category="external_api",
        input_schema_json={"type": "object", "properties": {"url": {"type": "string"}}},
        output_schema_json={"type": "object", "properties": {"status_code": {"type": "integer"}}},
        side_effect_level="external",
        timeout_seconds=5,
        dry_run_supported=True,
    )
    db_session.add(tool)
    await db_session.commit()

    output = await execute_tool(
        db=db_session, tool=tool, parameters={"url": "https://example.com"}, is_dry_run=True
    )

    assert output["status"] == "dry_run"
    assert "Would fetch" in output["message"]


@pytest.mark.asyncio
async def test_adapter_blocked_by_feature_flag(db_session: AsyncSession):
    settings = get_settings()
    settings.agent_tool_adapters_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_http_tool_enabled = False  # Disabled

    tool = AgentTool(
        id=uuid.uuid4(),
        name="http_get_tool",
        version="1.0.0",
        category="external_api",
        input_schema_json={"type": "object", "properties": {"url": {"type": "string"}}},
        output_schema_json={"type": "object", "properties": {"status_code": {"type": "integer"}}},
        side_effect_level="external",
        timeout_seconds=5,
    )
    db_session.add(tool)
    await db_session.commit()

    with pytest.raises(ValueError, match="HTTP tool is disabled by feature flag"):
        await execute_tool(db=db_session, tool=tool, parameters={"url": "https://example.com"})


from app.services.agents.tool_adapter_seeding import seed_tool_adapters
from app.services.agents.tool_registry import get_tool_by_name


@pytest.mark.asyncio
async def test_adapter_seeding(db_session: AsyncSession):
    # Ensure database is empty of these tools first (though setup_db handles it)
    await seed_tool_adapters(db_session)

    # Check if echo_tool was seeded
    echo_tool = await get_tool_by_name(db_session, "echo_tool")
    assert echo_tool is not None
    assert echo_tool.version == "1.0.0"
    assert echo_tool.side_effect_level == "none"

    # Check if shell_tool was seeded as disabled
    shell_tool = await get_tool_by_name(db_session, "shell_command_tool")
    assert shell_tool is not None
    assert shell_tool.enabled is False


@pytest.mark.asyncio
async def test_adapter_database_read_restriction(db_session: AsyncSession):
    settings = get_settings()
    settings.agent_tool_adapters_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_db_read_tool_enabled = True

    tool = AgentTool(
        id=uuid.uuid4(),
        name="database_read_tool",
        version="1.0.0",
        category="database_read",
        input_schema_json={"type": "object", "properties": {"query": {"type": "string"}}},
        output_schema_json={"type": "object"},
        side_effect_level="read",
        timeout_seconds=5,
    )
    db_session.add(tool)
    await db_session.commit()

    # Valid query
    output = await execute_tool(
        db=db_session, tool=tool, parameters={"table": "users", "query": "SELECT * FROM users"}
    )
    assert "rows" in output

    # Invalid query (mutation)
    with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
        await execute_tool(
            db=db_session, tool=tool, parameters={"table": "users", "query": "DELETE FROM users"}
        )
