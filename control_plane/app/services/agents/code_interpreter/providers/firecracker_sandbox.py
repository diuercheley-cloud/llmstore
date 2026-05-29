# Owner: agent-platform
import asyncio
import shutil
import time
import uuid
from typing import Any

from app.core.config import get_settings
from app.services.agents.code_interpreter.sandbox_policy import SandboxPolicyEngine


class FirecrackerSandboxProvider:
    name = "firecracker"
    mock = False

    def __init__(self):
        self.settings = get_settings()
        self.policy = SandboxPolicyEngine()

    async def run(self, code: str, limits: Any, session_id: uuid.UUID | None = None) -> dict[str, Any]:
        if not self.settings.agent_code_sandbox_firecracker_enabled:
            raise RuntimeError("Firecracker sandbox provider is disabled")
        
        fc_binary = shutil.which("firecracker")
        if fc_binary is None:
            if self.settings.agent_code_sandbox_microvm_required:
                raise RuntimeError("Firecracker provider is required but firecracker binary is not available")
            return {
                "status": "provider_unavailable",
                "error": "firecracker binary not found",
                "provider": self.name,
                "kernel_isolation_level": "microvm",
                "network_mode": "none",
                "filesystem_mode": "read-only-rootfs",
            }

        self.policy.validate_provider(self.name, is_simulated=False)

        raise NotImplementedError(
            "Real Firecracker MicroVM execution is not fully implemented. "
            "Simulated success is blocked in production."
        )
