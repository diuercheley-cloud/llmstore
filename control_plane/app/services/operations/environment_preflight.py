import asyncio
import importlib.util
import os
import sys
from typing import Dict, Any, List


# Owner: platform-ops

class EnvironmentPreflightService:
    """Hermetic validation of stack and dependencies."""

    def __init__(self):
        self.results = {}

    async def check_port(self, host: str, port: int, timeout: float = 1.0) -> bool:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except OSError:
            return False
        except asyncio.TimeoutError:
            return False

    async def run_full_preflight(self) -> Dict[str, Any]:
        """Runs all environment checks."""
        ports = await self._check_required_ports()
        dependencies = await self._check_python_deps()
        env_files = self._check_env_files()

        self.results = {
            "ports": ports,
            "dependencies": dependencies,
            "env_files": env_files,
            "status": "PASS"
        }

        failed_sections: List[str] = []
        if any(v == "FAIL" for v in ports.values()):
            failed_sections.append("ports")
        if any(v == "FAIL" for v in dependencies.values()):
            failed_sections.append("dependencies")
        if any(v == "FAIL" for v in env_files.values()):
            failed_sections.append("env_files")

        if failed_sections:
            self.results["status"] = "FAIL"
            self.results["failures"] = failed_sections

        return self.results

    async def _check_required_ports(self) -> Dict[str, str]:
        ports = {
            "postgres": 5432,
            "redis": 6379,
            "api": 8000
        }
        res = {}
        for name, port in ports.items():
            # In CI or local dev, we check localhost
            reachable = await self.check_port("127.0.0.1", port)
            res[name] = "PASS" if reachable else "FAIL"
        return res

    async def _check_python_deps(self) -> Dict[str, str]:
        required = ["fastapi", "sqlalchemy", "pydantic", "alembic"]
        res = {}
        for dep in required:
            res[dep] = "PASS" if importlib.util.find_spec(dep) else "FAIL"
        return res

    def _check_env_files(self) -> Dict[str, str]:
        files = [".env", ".env.example"]
        res = {}
        for f in files:
            res[f] = "PASS" if os.path.exists(f) else "FAIL"
        return res

if __name__ == "__main__":
    service = EnvironmentPreflightService()
    loop = asyncio.get_event_loop()
    report = loop.run_until_complete(service.run_full_preflight())
    print(report)
    if report["status"] == "FAIL":
        sys.exit(1)
