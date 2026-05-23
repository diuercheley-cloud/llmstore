import pytest
import pytest_asyncio
import uuid
from app.services.agents.tool_adapters.shell_command_tool import ShellCommandToolAdapter
from app.services.agents.tool_adapters.http_get_tool import HttpGetToolAdapter
from app.services.agents.tool_adapters.database_read_tool import DatabaseReadToolAdapter
from app.core.config import get_settings

@pytest.fixture
def setup_flags():
    settings = get_settings()
    orig_shell = settings.agent_shell_tool_enabled
    orig_http = settings.agent_http_tool_enabled
    orig_db = settings.agent_db_read_tool_enabled
    
    settings.agent_shell_tool_enabled = True
    settings.agent_http_tool_enabled = True
    settings.agent_db_read_tool_enabled = True
    
    yield
    
    settings.agent_shell_tool_enabled = orig_shell
    settings.agent_http_tool_enabled = orig_http
    settings.agent_db_read_tool_enabled = orig_db

@pytest.mark.asyncio
async def test_shell_blocks_non_allowlisted_command(setup_flags):
    adapter = ShellCommandToolAdapter()
    with pytest.raises(ValueError, match="not in the allowed shell command list"):
        await adapter.execute(command="rm", args=["-rf", "/"])

@pytest.mark.asyncio
async def test_shell_blocks_sensitive_files(setup_flags):
    adapter = ShellCommandToolAdapter()
    with pytest.raises(ValueError, match="sensitive path detected"):
        await adapter.execute(command="cat", args=[".env"])

@pytest.mark.asyncio
async def test_http_blocks_internal_ips(setup_flags):
    adapter = HttpGetToolAdapter()
    with pytest.raises(ValueError, match="strictly prohibited"):
        await adapter.execute(url="http://127.0.0.1:8080/admin")
    with pytest.raises(ValueError, match="strictly prohibited"):
        await adapter.execute(url="http://169.254.169.254/latest/meta-data")

@pytest.mark.asyncio
async def test_db_read_blocks_mutation(setup_flags):
    adapter = DatabaseReadToolAdapter()
    with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
        await adapter.execute(table="agent_runs", query="DELETE FROM agent_runs")
    with pytest.raises(ValueError, match="Only SELECT queries are allowed"):
        await adapter.execute(table="agent_runs", query="UPDATE agent_runs SET status='ok'")

@pytest.mark.asyncio
async def test_db_read_blocks_forbidden_tables(setup_flags):
    adapter = DatabaseReadToolAdapter()
    with pytest.raises(ValueError, match="not permitted"):
        await adapter.execute(table="users", query="SELECT * FROM users")
