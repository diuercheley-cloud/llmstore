import asyncio
import atexit
import contextlib
import logging
import os
import shlex
import signal
import subprocess
import sys
import uuid
from typing import Any

from .defaults import (
    DOCKER_CPU_LIMIT,
    DOCKER_MEMORY_LIMIT,
    DOCKER_PIDS_LIMIT,
    WORKSPACE_MOUNT_PATH,
)
from .platforms import get_platform, is_windows

logger = logging.getLogger(__name__)


class SandboxRunner:
    """
    Executes commands in an isolated environment (Docker or local).
    Ensures container cleanup and network isolation.
    Provides cross-platform support for Windows, macOS, and Linux.
    """

    def __init__(
        self,
        workspace,
        use_docker: bool = False,
        docker_image: str = "python:3.12-slim",
        workspace_mount_path: str = WORKSPACE_MOUNT_PATH,
        docker_memory_limit: str = DOCKER_MEMORY_LIMIT,
        docker_cpu_limit: str = DOCKER_CPU_LIMIT,
        docker_pids_limit: int = DOCKER_PIDS_LIMIT,
        network_mode: str = "none",
        proxy_url: str | None = None,
    ):
        self.workspace = workspace
        self.use_docker = use_docker
        self.docker_image = docker_image
        self.workspace_mount_path = workspace_mount_path
        self.docker_memory_limit = docker_memory_limit
        self.docker_cpu_limit = docker_cpu_limit
        self.docker_pids_limit = docker_pids_limit
        self.network_mode = network_mode
        self.proxy_url = proxy_url
        self.active_containers: set[str] = set()

        if self.use_docker:
            atexit.register(self._cleanup_all_containers)
            self._setup_signal_handlers()

        platform_name = get_platform()
        if is_windows():
            logger.info("Running on Windows. Local sandbox isolation is limited.")
        else:
            logger.debug(f"Running on {platform_name}.")

    def _setup_signal_handlers(self):
        """
        Registers handlers for SIGINT and SIGTERM to ensure cleanup.
        Handles platform differences (e.g., Windows limited signals).
        """

        def handler(signum, frame):
            logger.warning(f"Received signal {signum}, cleaning up...")
            self._cleanup_all_containers()
            sys.exit(1)

        try:
            # Main thread check
            if signal.getsignal(signal.SIGINT) == signal.default_int_handler:
                signal.signal(signal.SIGINT, handler)

            # SIGTERM might not be available on all non-Unix platforms,
            # though Python emulates it on Windows for signal.signal.
            if hasattr(signal, "SIGTERM"):
                signal.signal(signal.SIGTERM, handler)
        except (ValueError, RuntimeError):
            # Probably not the main thread or environment doesn't allow signal registration
            pass

    def _generate_container_name(self) -> str:
        return f"llm-harness-{uuid.uuid4().hex[:8]}"

    def _cleanup_all_containers(self):
        """
        Final cleanup of all registered containers.
        """
        if not self.active_containers:
            return

        # Copy list to avoid mutation error during iteration
        containers = list(self.active_containers)
        for name in containers:
            self._sync_cleanup_container(name)

    def _sync_cleanup_container(self, container_name: str):
        """
        Removes a container synchronously and forcibly.
        """
        if container_name in self.active_containers:
            logger.info(f"Cleaning up container {container_name}")
            try:
                subprocess.run(
                    ["docker", "rm", "-f", container_name],
                    capture_output=True,
                    check=False,
                    timeout=5,
                )
            except Exception as e:
                logger.error(f"Failed to cleanup container {container_name}: {e}")
            self.active_containers.discard(container_name)

    def _build_docker_command(self, command: str, container_name: str) -> str:
        """
        Builds the Docker command with security constraints and network mode.
        """
        quoted_command = shlex.quote(command)

        network_flag = f"--network {self.network_mode}"
        env_flags = ""
        if self.network_mode == "proxy" and self.proxy_url:
            env_flags = f"-e http_proxy={self.proxy_url} -e https_proxy={self.proxy_url}"

        return (
            f"docker run --name {container_name} --rm {network_flag} {env_flags} "
            f"--memory {self.docker_memory_limit} "
            f"--cpus {self.docker_cpu_limit} "
            f"--pids-limit {self.docker_pids_limit} "
            f"-v {shlex.quote(self.workspace.path)}:{self.workspace_mount_path} "
            f"-w {self.workspace_mount_path} {self.docker_image} sh -c {quoted_command}"
        )

    async def run_async(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        """
        Main asynchronous implementation.
        """
        from .tracing import Tracer
        with Tracer().trace_span("sandbox_run", attributes={"command": command}):
            if not self.use_docker:
                return await self._run_local_async(command, timeout)

        container_name = self._generate_container_name()
        self.active_containers.add(container_name)

        final_cmd = self._build_docker_command(command, container_name)
        logger.info(
            f"Executing in Docker sandbox (async): {command} [Name: {container_name}]"
        )

        process = await asyncio.create_subprocess_shell(
            final_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            rc = process.returncode if process.returncode is not None else 0
            return rc, stdout.decode(errors="replace"), stderr.decode(errors="replace")
        except TimeoutError:
            logger.warning(f"Command timed out after {timeout}s: {container_name}")
            return -1, "", "Command timed out"
        except Exception as e:
            logger.error(f"Error running command in sandbox: {e}")
            return 1, "", str(e)
        finally:
            self._sync_cleanup_container(container_name)

    async def _run_local_async(
        self, command: str, timeout: int = 30
    ) -> tuple[int, str, str]:
        logger.info(f"Executing in local sandbox (async): {command}")

        # Use process groups for cleanup on Unix-like systems
        kwargs: dict[str, Any] = {}
        if not is_windows():
            kwargs["preexec_fn"] = os.setsid

        process = await asyncio.create_subprocess_shell(
            command,
            cwd=self.workspace.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            rc = process.returncode if process.returncode is not None else 0
            return rc, stdout.decode(errors="replace"), stderr.decode(errors="replace")
        except TimeoutError:
            if is_windows():
                # On Windows, kill() is generally sufficient for shell processes,
                # though it won't kill child processes of the shell.
                process.kill()
            else:
                # On Unix, kill the entire process group
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            await process.wait()
            return -1, "", "Command timed out"

    def run(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        """
        Synchronous implementation.
        """
        if not self.use_docker:
            return self._run_local_sync(command, timeout)

        container_name = self._generate_container_name()
        self.active_containers.add(container_name)

        final_cmd = self._build_docker_command(command, container_name)
        logger.info(
            f"Executing in Docker sandbox (sync): {command} [Name: {container_name}]"
        )

        try:
            result = subprocess.run(
                final_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out after {timeout}s: {container_name}")
            return -1, "", "Command timed out"
        finally:
            self._sync_cleanup_container(container_name)

    def _run_local_sync(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        logger.info(f"Executing in local sandbox (sync): {command}")
        try:
            result = subprocess.run(
                command,
                cwd=self.workspace.path,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
