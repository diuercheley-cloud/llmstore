from pathlib import Path

import pytest
from app.core.config import get_settings
from app.services.agents.code_interpreter.sandbox_policy import (
    SandboxPolicyEngine,
    SandboxPolicyViolation,
)


@pytest.mark.asyncio
async def test_sandbox_policy_fails_closed_for_simulated_provider():
    settings = get_settings()
    settings.agent_sandbox_allow_simulated_provider = False
    policy = SandboxPolicyEngine()

    with pytest.raises(SandboxPolicyViolation):
        policy.validate_provider("mock", is_simulated=True)

    artifact = Path("artifacts/e2e/production-agentic/sandbox.md")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "## Sandbox Policy E2E\n- Simulated provider blocked in production posture: True\n",
        encoding="utf-8",
    )
