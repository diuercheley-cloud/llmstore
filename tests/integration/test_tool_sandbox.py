import pytest
from app.services.sandbox.base import SandboxLevel
from app.services.sandbox.service import SandboxService


@pytest.fixture
def sandbox_service():
    return SandboxService()


@pytest.mark.asyncio
async def test_dangerous_tool_promotes_level(sandbox_service):
    # 'shell_execute' is dangerous and should require at least WASI
    policy = sandbox_service._get_policy_for_tool("shell_execute", SandboxLevel.NONE)
    assert policy.required_level == SandboxLevel.WASI


@pytest.mark.asyncio
async def test_safe_tool_no_promotion(sandbox_service):
    # 'search_web' is considered safe enough for NONE (or local trusted)
    policy = sandbox_service._get_policy_for_tool("search_web", SandboxLevel.NONE)
    assert policy.required_level == SandboxLevel.NONE


@pytest.mark.asyncio
async def test_block_if_no_provider_available(sandbox_service):
    # If WASI is required but not available (current state of placeholder)
    result = await sandbox_service.execute_tool_safely("shell_execute", ["ls"], SandboxLevel.NONE)

    assert result.status == "blocked"
    assert "No provider available" in result.reason


@pytest.mark.asyncio
async def test_dry_run_noop_execution(sandbox_service):
    # Safe tool should use Noop provider if available
    result = await sandbox_service.execute_tool_safely("search_web", ["query"], SandboxLevel.NONE)

    assert result.status == "success"
    assert "Simulation" in result.stdout.decode()
    assert result.provider_name == "noop"


@pytest.mark.asyncio
async def test_mandatory_constraints(sandbox_service):
    policy = sandbox_service._get_policy_for_tool("shell_execute", SandboxLevel.NONE)

    assert policy.timeout_seconds > 0
    assert policy.memory_limit_mb > 0
