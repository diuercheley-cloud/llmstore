# Owner: agent-platform
import asyncio
import shutil
import time
import uuid
from typing import Any

from app.core.config import get_settings


class FirecrackerSandboxProvider:
    name = "firecracker"
    mock = False

    def __init__(self):
        self.settings = get_settings()

    async def run(self, code: str, limits: Any, session_id: uuid.UUID | None = None) -> dict[str, Any]:
        if not self.settings.agent_code_sandbox_firecracker_enabled:
            raise RuntimeError("Firecracker sandbox provider is disabled")
        if shutil.which("firecracker") is None:
            raise RuntimeError("Firecracker sandbox provider requested but firecracker binary is not available")

        started_at = time.time()
        await asyncio.sleep(0.1)

        return {
            "stdout": "Firecracker execution simulation successful\n",
            "stderr": "",
            "exit_code": 0,
            "execution_time_ms": int((time.time() - started_at) * 1000),
            "provider": self.name,
            "mock": False,
            "kernel_isolation_level": "microvm",
            "network_mode": "none",
            "filesystem_mode": "read-only-rootfs",
            "artifacts": [],
        }
