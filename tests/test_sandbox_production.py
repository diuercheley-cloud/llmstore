import pytest
import uuid
from app.core.config import get_settings
from app.services.agents.code_interpreter.sandbox_policy import SandboxPolicyEngine, SandboxPolicyViolation
from app.services.agents.code_interpreter.providers.mock_sandbox import MockSandboxProvider
from app.services.agents.code_interpreter.providers.gvisor_sandbox import GVisorSandboxProvider
from app.services.agents.code_interpreter.providers.firecracker_sandbox import FirecrackerSandboxProvider
from app.services.agents.tool_sandbox import execute_in_sandbox

@pytest.mark.asyncio
async def test_production_blocks_mock(session):
    settings = get_settings()
    settings.agent_sandbox_allow_simulated_provider = False

    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="Simulated provider 'mock' is not allowed"):
        policy.validate_provider("mock", is_simulated=True)

@pytest.mark.asyncio
async def test_microvm_required_blocks_docker(session):
    settings = get_settings()
    settings.agent_code_sandbox_microvm_required = True

    policy = SandboxPolicyEngine()
    with pytest.raises(SandboxPolicyViolation, match="MicroVM isolation is required"):
        policy.validate_provider("docker", is_simulated=False)


@pytest.mark.asyncio
async def test_firecracker_unavailable_fails_when_required():
    settings = get_settings()
    settings.agent_code_sandbox_firecracker_enabled = True
    settings.agent_code_sandbox_microvm_required = True
    
    # We assume 'firecracker' binary is NOT in path for this test
    provider = FirecrackerSandboxProvider()
    with pytest.raises(RuntimeError, match="firecracker binary is not available"):
        await provider.run("print(1)", None)

@pytest.mark.asyncio
async def test_gvisor_unavailable_fails_when_required():
    settings = get_settings()
    settings.agent_code_sandbox_gvisor_enabled = True
    settings.agent_code_sandbox_microvm_required = True
    
    # We assume 'runsc' binary is NOT in path for this test
    provider = GVisorSandboxProvider()
    with pytest.raises(RuntimeError, match="runsc/docker is not available"):
        await provider.run("print(1)", None)

@pytest.mark.asyncio
async def test_tool_sandbox_blocks_mock_in_production(session):
    settings = get_settings()
    settings.agent_sandbox_allow_simulated_provider = False
    
    with pytest.raises(ValueError, match="Simulated execution mode 'mock' is not allowed"):
        await execute_in_sandbox(
            db=session,
            tenant_id="t1",
            invocation_id=uuid.uuid4(),
            tool_name="test_tool",
            tool_category="test",
            parameters={},
            allowed_commands=[],
            timeout_seconds=10,
            sandbox_type="mock"
        )
