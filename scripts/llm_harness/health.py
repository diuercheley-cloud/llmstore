import logging
import os
import shutil
import sys
from typing import Any

from .sanitizer import Sanitizer

logger = logging.getLogger(__name__)


class HealthCheck:
    """
    Verifies the health of the environment and agentic services.
    """

    @staticmethod
    async def check_local_env() -> dict[str, Any]:
        project_pytest = os.path.exists(os.path.join(os.getcwd(), ".venv", "bin", "pytest"))
        project_venv = os.path.exists(os.path.join(os.getcwd(), ".venv", "bin", "python"))
        venv_by_prefix = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
        venv_by_path = os.path.sep + ".venv" + os.path.sep in sys.executable
        results = {
            "python_version": sys.version,
            "git_available": shutil.which("git") is not None,
            "pytest_available": shutil.which("pytest") is not None or project_pytest,
            "venv_active": (
                os.getenv("VIRTUAL_ENV") is not None
                or venv_by_prefix
                or venv_by_path
                or project_venv
            ),
        }
        critical_checks = [
            results["git_available"],
            results["pytest_available"],
            results["venv_active"],
        ]
        status = "healthy" if all(critical_checks) else "degraded"
        return {"status": status, "checks": results}

    @staticmethod
    async def check_provider(client) -> dict[str, Any]:
        try:
            return await client.health_check()
        except Exception as exc:
            return {
                "status": "unhealthy",
                "error": Sanitizer.sanitize_text(str(exc)),
                "message": Sanitizer.sanitize_text(str(exc)),
            }

    @staticmethod
    async def check_docker() -> dict[str, Any]:
        """Check if Docker is available and responsive."""
        import asyncio
        import subprocess

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode == 0:
                return {"status": "healthy", "docker": "available"}
            return {
                "status": "unhealthy",
                "docker": "unavailable",
                "error": Sanitizer.sanitize_text(stderr.decode(errors="replace")[:200]),
            }
        except FileNotFoundError:
            return {"status": "unhealthy", "docker": "not_installed"}
        except TimeoutError:
            return {"status": "unhealthy", "docker": "timeout"}
        except Exception as exc:
            return {
                "status": "unhealthy",
                "docker": "error",
                "error": Sanitizer.sanitize_text(str(exc)),
            }

    @staticmethod
    async def check_workspace(path: str) -> dict[str, Any]:
        """Check if workspace directory exists and is writable."""
        if not os.path.isdir(path):
            return {"status": "unhealthy", "workspace": "not_found", "path": path}

        writable = os.access(path, os.W_OK)
        if not writable:
            return {"status": "unhealthy", "workspace": "not_writable", "path": path}

        # Check disk space (warn if < 1GB free)
        try:
            stat = os.statvfs(path)
            free_bytes = stat.f_bavail * stat.f_frsize
            free_gb = free_bytes / (1024 ** 3)
            status = "healthy" if free_gb >= 1.0 else "degraded"
            return {
                "status": status,
                "workspace": "writable",
                "path": path,
                "free_disk_gb": round(free_gb, 2),
            }
        except OSError:
            return {"status": "healthy", "workspace": "writable", "path": path}

    @classmethod
    async def check_system(
        cls,
        client=None,
        workspace_path: str | None = None,
        check_docker: bool = False,
    ) -> dict[str, Any]:
        """Run all health checks and return composite status."""
        checks: dict[str, Any] = {}

        checks["local_env"] = await cls.check_local_env()

        if client is not None:
            checks["provider"] = await cls.check_provider(client)

        if check_docker:
            checks["docker"] = await cls.check_docker()

        if workspace_path is not None:
            checks["workspace"] = await cls.check_workspace(workspace_path)

        # Aggregate status: worst status wins
        statuses = [c.get("status", "unknown") for c in checks.values()]
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"
        else:
            overall = "healthy"

        return {"status": overall, "checks": checks}
