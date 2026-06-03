import logging
import os
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TestTools:
    """
    Automated testing tools for agents.
    """
    __test__ = False

    def __init__(self, sandbox, test_command: str = "pytest"):
        self.sandbox = sandbox
        self.test_command = test_command

    def _resolve_test_command(self) -> str:
        if shutil.which(self.test_command):
            return self.test_command

        project_pytest = os.path.join(os.getcwd(), ".venv", "bin", self.test_command)
        if os.path.exists(project_pytest):
            return project_pytest

        return self.test_command

    async def run_pytest(self, test_path: str = "tests/") -> dict[str, Any]:
        logger.info(f"Running pytest on {test_path}")
        report_path = "report.json"
        command_name = self._resolve_test_command()
        command = (
            f"{command_name} {test_path} "
            f"--json-report --json-report-file={report_path}"
        )

        returncode, stdout, stderr = await self.sandbox.run_async(command)
        if returncode != 0 and "--json-report" in stderr:
            fallback_command = f"{command_name} {test_path}"
            returncode, stdout, stderr = await self.sandbox.run_async(fallback_command)

        success = returncode == 0
        report_data: dict[str, Any] = {}
        workspace_path = getattr(self.sandbox.workspace, "path", None)
        if workspace_path:
            full_report = Path(workspace_path) / report_path
            if full_report.exists():
                try:
                    report_data = {"report_file": os.fspath(full_report)}
                except OSError:
                    report_data = {}

        return {
            "success": success,
            "exit_code": returncode,
            "output": stdout,
            "error": stderr,
            **report_data,
        }
