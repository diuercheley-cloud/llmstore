from unittest.mock import MagicMock, patch

from scripts.llm_harness.policy import PolicyEngine
from scripts.llm_harness.tools.git import GitTools


class TestGitTools:
    def setup_method(self):
        self.workspace = MagicMock()
        self.workspace.path = "/tmp/test-workspace"
        self.policy = PolicyEngine()
        self.git = GitTools(workspace=self.workspace, policy_engine=self.policy)

    @patch("scripts.llm_harness.tools.git.subprocess.run")
    def test_run_git_status(self, mock_run):
        with patch("scripts.llm_harness.tools.git.os.path.exists", return_value=True):
            mock_run.return_value = MagicMock(
                returncode=0, stdout="On branch main", stderr=""
            )
            result = self.git.run_git(["status"])
            assert "On branch main" in result
            mock_run.assert_called_once()

    def test_read_only_git_returns_empty_outside_repo(self):
        with patch("scripts.llm_harness.tools.git.os.path.exists", return_value=False):
            result = self.git.run_git(["status", "--porcelain"])
        assert result == ""

    @patch("scripts.llm_harness.tools.git.subprocess.run")
    def test_handles_command_failure(self, mock_run):
        with patch("scripts.llm_harness.tools.git.os.path.exists", return_value=True):
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="fatal: not a git repository"
            )
            result = self.git.run_git(["log"])
            assert "Error:" in result or "fatal" in result

    def test_blocks_git_push(self):
        result = self.git.run_git(["push", "origin", "main"])
        assert "blocked by policy" in result.lower()
