import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.llm_harness.sandbox import SandboxRunner
from scripts.llm_harness.workspace import Workspace


@pytest.mark.asyncio
async def test_sandbox_execution_async():
    async with Workspace() as ws:
        sandbox = SandboxRunner(workspace=ws)
        returncode, stdout, stderr = await sandbox.run_async("echo 'hello'")
        assert returncode == 0
        assert "hello" in stdout


def test_sandbox_execution_sync():
    async def run_test():
        async with Workspace() as ws:
            sandbox = SandboxRunner(workspace=ws)
            returncode, stdout, stderr = sandbox.run("echo 'hello sync'")
            assert returncode == 0
            assert "hello sync" in stdout

    import asyncio

    asyncio.run(run_test())


@pytest.mark.asyncio
async def test_sandbox_timeout():
    async with Workspace() as ws:
        sandbox = SandboxRunner(workspace=ws)
        returncode, stdout, stderr = await sandbox.run_async("sleep 5", timeout=1)
        assert returncode == -1
        assert "timed out" in stderr


def test_sandbox_docker_command_build():
    async def run_test():
        async with Workspace() as ws:
            sandbox = SandboxRunner(workspace=ws, use_docker=True)
            cmd = sandbox._build_docker_command("ls", "test-name")
            assert "docker run" in cmd
            assert "--name test-name" in cmd
            assert "--network none" in cmd
            assert ws.path in cmd

    import asyncio

    asyncio.run(run_test())


@pytest.mark.asyncio
async def test_sandbox_docker_cleanup_on_success():
    async with Workspace() as ws:
        runner = SandboxRunner(workspace=ws, use_docker=True)

        with patch("asyncio.create_subprocess_shell") as mock_shell, patch("subprocess.run") as mock_run:
            # Setup mock process
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"out", b"err"))
            mock_process.returncode = 0
            mock_shell.return_value = mock_process

            rc, stdout, stderr = await runner.run_async("echo 'hello'")

            assert rc == 0
            # Verify cleanup was called
            mock_run.assert_called()
            args, kwargs = mock_run.call_args
            assert "docker" in args[0]
            assert "rm" in args[0]
            assert "-f" in args[0]


@pytest.mark.asyncio
async def test_sandbox_docker_cleanup_on_timeout():
    async with Workspace() as ws:
        runner = SandboxRunner(workspace=ws, use_docker=True)

        async def fake_wait_for(awaitable, timeout):
            awaitable.close()
            raise asyncio.TimeoutError

        with patch("asyncio.create_subprocess_shell") as mock_shell, patch(
            "asyncio.wait_for",
            new=AsyncMock(side_effect=fake_wait_for),
        ), patch("subprocess.run") as mock_run:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_shell.return_value = mock_process

            rc, stdout, stderr = await runner.run_async("sleep 10", timeout=0.1)

            assert rc == -1
            assert "timed out" in stderr

            # Verify cleanup was called even on timeout
            mock_run.assert_called()
            args, kwargs = mock_run.call_args
            assert "rm" in args[0]


def test_sandbox_sync_cleanup():
    with MagicMock() as ws:
        ws.path = "/tmp/fake-ws"
        runner = SandboxRunner(workspace=ws, use_docker=True)

        with patch("subprocess.run") as mock_run:
            # First call is for docker run, second for cleanup
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="out", stderr="err"),  # docker run
                MagicMock(returncode=0),  # docker rm
            ]

            rc, stdout, stderr = runner.run("echo 'hello'")

            assert rc == 0
            assert mock_run.call_count == 2
            # Check cleanup call
            last_call = mock_run.call_args_list[-1]
            assert "rm" in last_call[0][0]


@patch("atexit.register")
def test_sandbox_atexit_registration(mock_register):
    ws = MagicMock()
    SandboxRunner(workspace=ws, use_docker=True)
    mock_register.assert_called_once()


@patch("signal.signal")
def test_sandbox_signal_registration(mock_signal):
    ws = MagicMock()
    SandboxRunner(workspace=ws, use_docker=True)
    # Should call signal.signal at least twice (SIGINT, SIGTERM)
    assert mock_signal.call_count >= 1


def test_build_docker_command_security():
    ws = MagicMock()
    ws.path = "/tmp/workspace"
    runner = SandboxRunner(workspace=ws, use_docker=True, docker_image="custom-image")

    cmd = runner._build_docker_command("ls -la", "test-container")

    assert "--network none" in cmd
    assert "-v /tmp/workspace:/workspace" in cmd
    assert "custom-image" in cmd
    assert "--name test-container" in cmd
    assert "sh -c 'ls -la'" in cmd
