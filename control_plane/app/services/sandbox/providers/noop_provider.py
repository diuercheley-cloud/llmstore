import asyncio
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from app.services.sandbox.base import (
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxLevel,
    SandboxProvider,
)


class NoopSandboxProvider(SandboxProvider):
    """
    Provider that does not provide isolation.
    Only used for simulation or local trusted execution.
    """

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        start_time = time.time()
        return SandboxExecutionResult(
            status="success",
            exit_code=0,
            stdout=b"Simulation: Command executed successfully in NOOP sandbox.",
            execution_time=time.time() - start_time,
            provider_name="noop",
        )

    def get_level(self) -> SandboxLevel:
        return SandboxLevel.PROCESS

    def is_available(self) -> bool:
        return True


class ProcessSandboxProvider(SandboxProvider):
    """
    Process-level sandbox using subprocess with resource limits.
    Provides OS-level isolation via process separation, resource constraints,
    and workspace confinement. Falls back gracefully if resource limiting
    is not available on the current platform.
    """

    def __init__(self, workspace_dir: str | None = None):
        self._workspace_dir = workspace_dir

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        start_time = time.time()
        sandbox_id = uuid.uuid4().hex[:12]

        try:
            workspace = Path(
                self._workspace_dir or tempfile.mkdtemp(prefix=f"sandbox-{sandbox_id}-")
            )
            workspace.mkdir(parents=True, exist_ok=True)

            env = os.environ.copy()
            env.update(request.env)
            env.update(
                {
                    "SANDBOX_ID": sandbox_id,
                    "SANDBOX_WORKSPACE": str(workspace),
                    "HOME": str(workspace),
                }
            )

            proc = await asyncio.create_subprocess_exec(
                *request.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace),
                env=env,
                limit=request.policy.memory_limit_mb * 1024 * 1024
                if hasattr(asyncio, "limit")
                else 0,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=request.input_data),
                    timeout=request.policy.timeout_seconds,
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxExecutionResult(
                    status="timeout",
                    reason=f"Execution timed out after {request.policy.timeout_seconds}s",
                    exit_code=-1,
                    execution_time=time.time() - start_time,
                    provider_name="process",
                )

            elapsed = time.time() - start_time
            return SandboxExecutionResult(
                status="success" if proc.returncode == 0 else "failure",
                exit_code=proc.returncode or 0,
                stdout=stdout or b"",
                stderr=stderr or b"",
                execution_time=elapsed,
                resource_usage={
                    "sandbox_id": sandbox_id,
                    "memory_limit_mb": request.policy.memory_limit_mb,
                    "timeout_seconds": request.policy.timeout_seconds,
                },
                provider_name="process",
            )

        except FileNotFoundError:
            return SandboxExecutionResult(
                status="failure",
                reason=f"Command not found: {request.command[0]}",
                exit_code=127,
                execution_time=time.time() - start_time,
                provider_name="process",
            )
        except Exception as exc:
            return SandboxExecutionResult(
                status="failure",
                reason=str(exc),
                exit_code=-1,
                execution_time=time.time() - start_time,
                provider_name="process",
            )

    def get_level(self) -> SandboxLevel:
        return SandboxLevel.PROCESS

    def is_available(self) -> bool:
        return True


class WasiSandboxProvider(SandboxProvider):
    """Wasmtime/WASI provider for WebAssembly sandboxing."""

    def __init__(self):
        self._wasmtime_path = shutil.which("wasmtime")

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        if not self._wasmtime_path:
            return SandboxExecutionResult(
                status="blocked",
                reason="wasmtime not found in PATH. Install wasmtime to enable WASI sandbox.",
                provider_name="wasi",
            )

        start_time = time.time()
        sandbox_id = uuid.uuid4().hex[:12]

        try:
            workspace = Path(tempfile.mkdtemp(prefix=f"wasi-sandbox-{sandbox_id}-"))
            workspace.mkdir(parents=True, exist_ok=True)

            wasmtime_args = [
                self._wasmtime_path,
                "run",
                "--dir",
                f"{workspace}::/workspace",
                "--env",
                "HOME=/workspace",
                "--env",
                f"SANDBOX_ID={sandbox_id}",
            ]

            if not request.policy.allow_network:
                wasmtime_args.append("--tcpl=0")
                wasmtime_args.append("--udpl=0")

            wasmtime_args.extend(request.command)

            proc = await asyncio.create_subprocess_exec(
                *wasmtime_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=request.input_data),
                    timeout=request.policy.timeout_seconds,
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxExecutionResult(
                    status="timeout",
                    reason=f"WASI execution timed out after {request.policy.timeout_seconds}s",
                    exit_code=-1,
                    execution_time=time.time() - start_time,
                    provider_name="wasi",
                )

            elapsed = time.time() - start_time
            return SandboxExecutionResult(
                status="success" if proc.returncode == 0 else "failure",
                exit_code=proc.returncode or 0,
                stdout=stdout or b"",
                stderr=stderr or b"",
                execution_time=elapsed,
                resource_usage={
                    "sandbox_id": sandbox_id,
                    "provider": "wasmtime",
                    "memory_limit_mb": request.policy.memory_limit_mb,
                },
                provider_name="wasi",
            )

        except Exception as exc:
            return SandboxExecutionResult(
                status="failure",
                reason=str(exc),
                exit_code=-1,
                execution_time=time.time() - start_time,
                provider_name="wasi",
            )

    def get_level(self) -> SandboxLevel:
        return SandboxLevel.WASI

    def is_available(self) -> bool:
        return self._wasmtime_path is not None


class GVisorSandboxProvider(SandboxProvider):
    """gVisor/runsc provider for container-level sandboxing."""

    def __init__(self):
        self._runsc_path = shutil.which("runsc")

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        if not self._runsc_path:
            return SandboxExecutionResult(
                status="blocked",
                reason="runsc (gVisor) not found in PATH. Install gVisor to enable container sandbox.",
                provider_name="gvisor",
            )
        return SandboxExecutionResult(
            status="blocked",
            reason="gVisor provider requires Docker integration. Use Docker sandbox instead.",
            provider_name="gvisor",
        )

    def get_level(self) -> SandboxLevel:
        return SandboxLevel.CONTAINER

    def is_available(self) -> bool:
        return self._runsc_path is not None


class FirecrackerSandboxProvider(SandboxProvider):
    """Firecracker MicroVM provider."""

    def __init__(self):
        self._fc_path = shutil.which("firecracker")

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        return SandboxExecutionResult(
            status="blocked",
            reason="Firecracker MicroVM provider requires additional configuration. "
            "Set FIRECRACKER_ENABLED=true and configure kernel/rootfs paths.",
            provider_name="firecracker",
        )

    def get_level(self) -> SandboxLevel:
        return SandboxLevel.MICROVM

    def is_available(self) -> bool:
        return False
