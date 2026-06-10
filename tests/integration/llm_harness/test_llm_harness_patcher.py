import time
from unittest.mock import MagicMock, patch

import pytest

from scripts.llm_harness.patcher import Patcher
from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.workspace import Workspace


@pytest.mark.asyncio
async def test_patcher_apply_valid():
    async with Workspace() as ws:
        policy = PolicyEngine()
        ws.write_file("a.py", "x = 1")
        patcher = Patcher(workspace=ws, policy_engine=policy)

        diff = "--- a.py\n+++ a.py\n@@ -1 +1 @@\n-x = 1\n+x = 2"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = patcher.apply_patch(diff)

            assert result.success is True
            assert result.mode == "apply"
            assert result.diff_sha256
            # Verify that git apply was invoked exactly once.
            assert mock_run.call_count == 1
            args, kwargs = mock_run.call_args
            assert "git" in args[0]
            assert "apply" in args[0]
            assert "--check" not in args[0]


@pytest.mark.asyncio
async def test_patcher_dry_run():
    async with Workspace() as ws:
        policy = PolicyEngine()
        patcher = Patcher(workspace=ws, policy_engine=policy)
        diff = "--- a.py\n+++ a.py\n@@ -1 +1 @@\n-x = 1\n+x = 2"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = patcher.apply_patch(diff, dry_run=True)

            assert result.success is True
            assert result.mode == "check"
            assert result.diff_sha256
            assert mock_run.call_count == 1
            args, _ = mock_run.call_args
            assert "--check" in args[0]


@pytest.mark.asyncio
async def test_patcher_invalid_format():
    async with Workspace() as ws:
        policy = PolicyEngine()
        patcher = Patcher(workspace=ws, policy_engine=policy)

        result = patcher.apply_patch("not a diff")
        assert result.success is False
        assert "Invalid unified diff format" in result.error
        assert result.diff_sha256


@pytest.mark.asyncio
async def test_patcher_blocked_path():
    async with Workspace() as ws:
        policy = PolicyEngine()
        patcher = Patcher(workspace=ws, policy_engine=policy)

        diff = "--- policy.py\n+++ policy.py\n..."
        result = patcher.apply_patch(diff)
        assert result.success is False
        assert "Blocked by policy" in result.error


def test_patcher_replace_legacy_compat():
    async def run():
        async with Workspace() as ws:
            policy = PolicyEngine()
            ws.write_file("code.py", "x = 1")
            patcher = Patcher(workspace=ws, policy_engine=policy)
            success = patcher.replace_content("code.py", "x = 1", "x = 2")
            assert success is True
            assert ws.read_file("code.py") == "x = 2"

    import asyncio

    asyncio.run(run())


def test_patcher_large_file_efficiency():
    async def run():
        async with Workspace() as ws:
            policy = PolicyEngine()
            content = "line\n" * 1000
            ws.write_file("large.py", content)
            patcher = Patcher(workspace=ws, policy_engine=policy)

            diff = "--- large.py\n+++ large.py\n@@ -1 +1 @@\n-line\n+new"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                start = time.time()
                patcher.apply_patch(diff)
                duration = time.time() - start

                assert mock_run.call_count == 1
                assert duration < 0.1

    import asyncio

    asyncio.run(run())
