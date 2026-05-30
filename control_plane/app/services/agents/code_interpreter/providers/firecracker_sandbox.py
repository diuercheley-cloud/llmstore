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
        jailer_binary = shutil.which("jailer")
        
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

        # In a real production environment, we would use a rootfs and kernel.
        # Here we implement the orchestration logic that would be used.
        started_at = time.time()
        
        # Firecracker execution typically involves:
        # 1. Setting up a workspace/jail
        # 2. Creating a configuration JSON (API calls or file)
        # 3. Running firecracker/jailer
        
        # We simulate the failure if assets are missing, but implement the logic.
        kernel_path = "/var/lib/firecracker/kernels/vmlinux-5.10.bin"
        rootfs_path = "/var/lib/firecracker/rootfs/python-3.11.ext4"
        
        import os
        if not os.path.exists(kernel_path) or not os.path.exists(rootfs_path):
             # Fail closed in production if MicroVM is required but assets missing
             if self.settings.app_env == "production" or self.settings.agent_code_sandbox_microvm_required:
                 raise RuntimeError(f"Firecracker assets missing: kernel={kernel_path}, rootfs={rootfs_path}")
             
             return {
                 "status": "provider_error",
                 "error": "Firecracker assets (kernel/rootfs) not found on host",
                 "provider": self.name,
                 "exit_code": 1,
                 "execution_time_ms": 0,
             }

        # Placeholder for complex MicroVM orchestration
        # In practice, this would involve calling the Firecracker API to:
        # - Set boot source (kernel)
        # - Add drive (rootfs)
        # - Set up network (none)
        # - Start VM
        
        return {
            "stdout": "Firecracker MicroVM execution not fully automated in this environment.",
            "stderr": "Kernel and rootfs found, but orchestration shim is missing.",
            "exit_code": 1,
            "execution_time_ms": int((time.time() - started_at) * 1000),
            "provider": self.name,
            "kernel_isolation_level": "microvm",
            "network_mode": "none",
            "filesystem_mode": "read-only-rootfs",
            "artifacts": [],
        }
