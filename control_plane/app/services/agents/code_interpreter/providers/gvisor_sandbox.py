# Owner: agent-platform
import asyncio
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.agents.code_interpreter.sandbox_policy import SandboxPolicyEngine


class GVisorSandboxProvider:
    name = "gvisor"
    mock = False

    def __init__(self):
        self.settings = get_settings()
        self.policy = SandboxPolicyEngine()

    async def run(self, code: str, limits: Any, session_id: uuid.UUID | None = None) -> dict[str, Any]:
        if not self.settings.agent_code_sandbox_gvisor_enabled:
            raise RuntimeError("gVisor sandbox provider is disabled")

        runsc_path = shutil.which("runsc")
        docker_path = shutil.which("docker")
        
        if runsc_path is None or docker_path is None:
            if self.settings.agent_code_sandbox_microvm_required:
                raise RuntimeError("gVisor provider is required but runsc/docker is not available")
            return {
                "status": "provider_unavailable",
                "error": "runsc or docker binary not found",
                "provider": self.name,
                "kernel_isolation_level": "user-space-kernel",
                "network_mode": "none",
                "filesystem_mode": "read-only-rootfs",
            }

        self.policy.validate_provider(self.name, is_simulated=False)

        started_at = time.time()

        with tempfile.TemporaryDirectory(prefix="agent-gvisor-sandbox-") as tmpdir:
            workdir = Path(tmpdir)
            program_path = workdir / "program.py"
            program_path.write_text(code, encoding="utf-8")

            command = [
                "docker",
                "run",
                "--rm",
                "--runtime=runsc",
                "--network=none",
                "--read-only",
                "--user",
                "65534:65534",
                "--security-opt=no-new-privileges",
                "--cap-drop=ALL",
                "--memory",
                f"{limits.memory_limit_mb}m",
                "--tmpfs",
                f"/tmp:size={limits.writable_tmp_size_mb}m,noexec,nosuid,nodev",
                "--add-host",
                "169.254.169.254:0.0.0.0",
                "--add-host",
                "169.254.170.2:0.0.0.0",
                "--add-host",
                "metadata.google.internal:0.0.0.0",
                "-v",
                f"{program_path}:/workspace/program.py:ro",
                "-w",
                "/workspace",
                "python:3.11-alpine",
                "python",
                "program.py",
            ]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=limits.timeout_seconds)
                exit_code = proc.returncode
            except Exception as e:
                stdout = b""
                stderr = f"gVisor execution failed: {str(e)}".encode("utf-8")
                exit_code = 1

        return {
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore"),
            "exit_code": exit_code,
            "execution_time_ms": int((time.time() - started_at) * 1000),
            "provider": self.name,
            "mock": False,
            "kernel_isolation_level": "user-space-kernel",
            "network_mode": "none",
            "filesystem_mode": "read-only-rootfs",
            "artifacts": [],
        }
