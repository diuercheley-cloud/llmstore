# Owner: agent-platform
import asyncio
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


class DockerSandboxProvider:
    name = "docker"
    mock = False

    async def run(self, code: str, limits: Any, session_id: uuid.UUID | None = None) -> dict[str, Any]:
        if shutil.which("docker") is None:
            raise RuntimeError("Docker sandbox provider requested but docker binary is not available")

        started_at = time.time()
        with tempfile.TemporaryDirectory(prefix="agent-code-sandbox-") as tmpdir:
            workdir = Path(tmpdir)
            program_path = workdir / "program.py"
            program_path.write_text(code, encoding="utf-8")

            command = [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--read-only",
                "--pids-limit=64",
                "--memory",
                f"{limits.memory_limit_mb}m",
                "--cpus=1.0",
                "--tmpfs",
                f"/tmp:size={limits.writable_tmp_size_mb}m,noexec,nosuid,nodev",
                "-v",
                f"{program_path}:/workspace/program.py:ro",
                "-w",
                "/workspace",
                "python:3.11-alpine",
                "python",
                "program.py",
            ]

            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=limits.timeout_seconds)
                exit_code = proc.returncode
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                stdout = b""
                stderr = f"Execution timed out after {limits.timeout_seconds} seconds.".encode("utf-8")
                exit_code = 124

        return {
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore"),
            "exit_code": exit_code,
            "execution_time_ms": int((time.time() - started_at) * 1000),
            "provider": self.name,
            "mock": False,
            "artifacts": [],
        }
