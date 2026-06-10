
from unittest.mock import MagicMock, patch

import pytest

from scripts.llm_harness.policy import PolicyDecision, PolicyEngine
from scripts.llm_harness.tools.git import GitTools


class TestGitTool:
    @pytest.fixture
    def mock_workspace(self, tmp_path):
        ws = MagicMock()
        ws.path = str(tmp_path)
        (tmp_path / ".git").mkdir()
        return ws

    @pytest.fixture
    def policy_engine(self):
        return PolicyEngine()

    def test_git_status(self, mock_workspace, policy_engine):
        git = GitTools(workspace=mock_workspace, policy_engine=policy_engine)
        with patch("scripts.llm_harness.tools.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="On branch main", stderr="")
            result = git.run_git(["status"])
            assert "On branch main" in result
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["git", "status"]

    def test_git_diff(self, mock_workspace, policy_engine):
        git = GitTools(workspace=mock_workspace, policy_engine=policy_engine)
        with patch("scripts.llm_harness.tools.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="diff content", stderr="")
            result = git.run_git(["diff"])
            assert "diff content" in result
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["git", "diff"]

    def test_git_error(self, mock_workspace, policy_engine):
        git = GitTools(workspace=mock_workspace, policy_engine=policy_engine)
        with patch("scripts.llm_harness.tools.git.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="fatal: not a git repo")
            result = git.run_git(["log"])
            assert "Error:" in result
            assert "fatal: not a git repo" in result

    def test_policy_blocking_dangerous_args(self, mock_workspace):
        policy = MagicMock(spec=PolicyEngine)
        policy.evaluate_shell_command.return_value = PolicyDecision(
            allowed=False, reason="Blocked by test policy"
        )
        git = GitTools(workspace=mock_workspace, policy_engine=policy)
        
        result = git.run_git(["push", "origin", "master"])
        assert "Error: Command blocked by policy" in result
        assert "Blocked by test policy" in result
        policy.evaluate_shell_command.assert_called_with("git push origin master")
