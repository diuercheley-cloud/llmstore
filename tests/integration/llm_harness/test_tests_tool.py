
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.llm_harness.tools.tests import TestTools


class TestTestTools:
    @pytest.fixture
    def mock_sandbox(self):
        sandbox = MagicMock()
        sandbox.run_async = AsyncMock()
        sandbox.workspace = MagicMock()
        sandbox.workspace.path = "/fake/workspace"
        return sandbox

    @pytest.mark.asyncio
    async def test_run_pytest_default(self, mock_sandbox):
        mock_sandbox.run_async.return_value = (0, "all tests passed", "")
        test_tools = TestTools(sandbox=mock_sandbox)
        
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            result = await test_tools.run_pytest("tests/")
            
            assert result["success"] is True
            assert result["exit_code"] == 0
            assert "all tests passed" in result["output"]
            
            mock_sandbox.run_async.assert_called_once()
            command = mock_sandbox.run_async.call_args[0][0]
            assert "pytest tests/" in command
            assert "--json-report" in command

    @pytest.mark.asyncio
    async def test_run_pytest_custom_command(self, mock_sandbox):
        mock_sandbox.run_async.return_value = (0, "custom runner ok", "")
        test_tools = TestTools(sandbox=mock_sandbox, test_command="my-pytest")
        
        with patch("shutil.which", side_effect=lambda x: "/bin/my-pytest" if x == "my-pytest" else None):
            result = await test_tools.run_pytest()
            
            assert result["success"] is True
            mock_sandbox.run_async.assert_called_once()
            command = mock_sandbox.run_async.call_args[0][0]
            assert "my-pytest tests/" in command

    @pytest.mark.asyncio
    async def test_run_pytest_timeout(self, mock_sandbox):
        # Sandbox returns -1 for timeout
        mock_sandbox.run_async.return_value = (-1, "", "Command timed out")
        test_tools = TestTools(sandbox=mock_sandbox)
        
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            result = await test_tools.run_pytest()
            
            assert result["success"] is False
            assert result["exit_code"] == -1
            assert "Command timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_run_pytest_parsed_output(self, mock_sandbox):
        mock_sandbox.run_async.return_value = (0, "pass", "")
        test_tools = TestTools(sandbox=mock_sandbox)
        
        report_file = Path(mock_sandbox.workspace.path) / "report.json"
        
        with patch("shutil.which", return_value="/usr/bin/pytest"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("os.fspath", return_value=str(report_file)):
            
            result = await test_tools.run_pytest()
            assert "report_file" in result
            assert result["report_file"] == str(report_file)
