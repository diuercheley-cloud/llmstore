import pytest

from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.sandbox import SandboxRunner
from scripts.llm_harness.tools.files import FileTools
from scripts.llm_harness.tools.shell import ShellTools
from scripts.llm_harness.tools.tests import TestTools
from scripts.llm_harness.workspace import Workspace


@pytest.mark.asyncio
async def test_file_tools():
    async with Workspace() as ws:
        file_tools = FileTools(workspace=ws)
        file_tools.write_file("test.txt", "content")
        assert file_tools.read_file("test.txt") == "content"
        assert "test.txt" in file_tools.list_files()

@pytest.mark.asyncio
async def test_shell_tools_async():
    async with Workspace() as ws:
        policy = PolicyEngine()
        sandbox = SandboxRunner(workspace=ws)
        shell_tools = ShellTools(sandbox_runner=sandbox, policy_engine=policy)
        result = await shell_tools.run_shell_async("echo 'hi'")
        assert "hi" in result.output
        assert result.returncode == 0

def test_shell_tools_sync():
    async def run_test():
        async with Workspace() as ws:
            policy = PolicyEngine()
            sandbox = SandboxRunner(workspace=ws)
            shell_tools = ShellTools(sandbox_runner=sandbox, policy_engine=policy)
            result = shell_tools.run_shell("echo 'hi sync'")
            assert "hi sync" in result.output
            assert result.returncode == 0
    import asyncio
    asyncio.run(run_test())

@pytest.mark.asyncio
async def test_shell_tools_blocked():
    async with Workspace() as ws:
        policy = PolicyEngine()
        sandbox = SandboxRunner(workspace=ws)
        shell_tools = ShellTools(sandbox_runner=sandbox, policy_engine=policy)
        result = await shell_tools.run_shell_async("ls; rm -rf /")
        assert result.blocked is True
        assert "Dangerous shell operator" in result.reason


@pytest.mark.asyncio
async def test_shell_tools_allow_rm_tmp_only_when_policy_allows():
    async with Workspace() as ws:
        ws.write_file("tmp/file.txt", "content")
        policy = PolicyEngine(
            {
                "shell_policy": {
                    "workspace_root": ws.path,
                    "path_exceptions": [
                        {
                            "command": "rm",
                            "args": ["-rf"],
                            "path": "./tmp",
                        }
                    ],
                }
            }
        )
        sandbox = SandboxRunner(workspace=ws)
        shell_tools = ShellTools(sandbox_runner=sandbox, policy_engine=policy)

        allowed = await shell_tools.run_shell_async("rm -rf ./tmp")
        denied = await shell_tools.run_shell_async("rm -rf /")

        assert allowed.blocked is False
        assert allowed.returncode == 0
        assert denied.blocked is True
        assert "always denied" in denied.reason.lower()


@pytest.mark.asyncio
async def test_file_tools_block_sensitive_path():
    async with Workspace() as ws:
        policy = PolicyEngine()
        file_tools = FileTools(workspace=ws, policy_engine=policy)
        with pytest.raises(PermissionError):
            file_tools.read_file(".env")


@pytest.mark.asyncio
async def test_test_tools_run_pytest_uses_sandbox_runner():
    async with Workspace() as ws:
        ws.write_file(
            "tests/test_sample.py",
            "def test_ok():\n    assert True\n",
        )
        sandbox = SandboxRunner(workspace=ws)
        test_tools = TestTools(sandbox=sandbox)
        result = await test_tools.run_pytest("tests/")
        assert result["success"] is True
        assert result["exit_code"] == 0
        if "report_file" in result:
            assert result["report_file"].endswith("report.json")
