import logging
import os
import signal
import subprocess
from uuid import UUID

import httpx
from app.contracts.backend_lifecycle import (
    BackendDesiredState,
    BackendLifecycleCapabilities,
    BackendObservedState,
    LifecycleActionResult,
)
from app.services.backend_lifecycle.providers.base import BaseLifecycleProvider

logger = logging.getLogger(__name__)


class LocalProcessProvider(BaseLifecycleProvider):
    _processes: dict[UUID, subprocess.Popen] = {}

    def capabilities(self) -> BackendLifecycleCapabilities:
        return BackendLifecycleCapabilities(
            can_start=True,
            can_stop=True,
            can_restart=True,
            can_observe=True,
            provider_type="local_process",
        )

    async def get_observed_state(self, backend_id: UUID, desired: BackendDesiredState) -> BackendObservedState:
        proc = self._processes.get(backend_id)
        if proc is None or proc.poll() is not None:
            return BackendObservedState(
                backend_id=backend_id,
                provider=desired.provider,
                running=False,
                healthy=False,
                error="no local process found",
            )
        healthy = await self._check_health(desired.backend_url)
        return BackendObservedState(
            backend_id=backend_id,
            provider=desired.provider,
            running=True,
            healthy=healthy,
            pid=proc.pid,
            url=desired.backend_url,
        )

    async def start_backend(self, backend_id: UUID, desired: BackendDesiredState) -> LifecycleActionResult:
        if backend_id in self._processes:
            proc = self._processes[backend_id]
            if proc.poll() is None:
                return LifecycleActionResult(
                    success=True,
                    action="start",
                    backend_id=backend_id,
                    message="backend already running",
                )
        try:
            cmd = self._build_command(desired)
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
            )
            self._processes[backend_id] = proc
            logger.info("started local process for backend %s (pid=%s)", desired.name, proc.pid)
            return LifecycleActionResult(
                success=True,
                action="start",
                backend_id=backend_id,
                message=f"started with pid {proc.pid}",
            )
        except Exception as exc:
            logger.error("failed to start local process: %s", exc)
            return LifecycleActionResult(
                success=False,
                action="start",
                backend_id=backend_id,
                message=str(exc),
                error=str(exc),
            )

    async def stop_backend(self, backend_id: UUID, desired: BackendDesiredState) -> LifecycleActionResult:
        proc = self._processes.pop(backend_id, None)
        if proc is None or proc.poll() is not None:
            return LifecycleActionResult(
                success=True,
                action="stop",
                backend_id=backend_id,
                message="no running process found",
            )
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=5)
            logger.info("stopped local process for backend %s (pid=%s)", desired.name, proc.pid)
            return LifecycleActionResult(
                success=True,
                action="stop",
                backend_id=backend_id,
                message="process stopped",
            )
        except Exception as exc:
            logger.error("failed to stop local process: %s", exc)
            return LifecycleActionResult(
                success=False,
                action="stop",
                backend_id=backend_id,
                message=str(exc),
                error=str(exc),
            )

    async def restart_backend(self, backend_id: UUID, desired: BackendDesiredState) -> LifecycleActionResult:
        stop_result = await self.stop_backend(backend_id, desired)
        if not stop_result.success:
            return stop_result
        return await self.start_backend(backend_id, desired)

    def _build_command(self, desired: BackendDesiredState) -> list[str]:
        if desired.provider == "llama.cpp":
            return ["llama-server", "-m", "/models/model.gguf", "--host", "0.0.0.0", "--port", "8080"]
        return ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

    async def _check_health(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{url}/health", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False
