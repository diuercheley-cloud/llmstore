import logging
import os
import subprocess

from ..cache import LocalCache
from ..policy import PolicyEngine

logger = logging.getLogger(__name__)


class GitTools:
    """
    Governed git tools for agents.
    """

    def __init__(
        self,
        workspace,
        policy_engine: PolicyEngine | None = None,
        cache: LocalCache | None = None,
        repo_snapshot_hash_getter=None,
        policy_hash: str = "",
    ):
        self.workspace = workspace
        self.policy_engine = policy_engine or PolicyEngine()
        self.cache = cache
        self.repo_snapshot_hash_getter = repo_snapshot_hash_getter
        self.policy_hash = policy_hash

    def _is_read_only_git(self, args: list) -> bool:
        if not args:
            return False
        subcommand = str(args[0])
        return subcommand in {"status", "diff", "rev-parse", "ls-files", "show"}

    def _has_git_metadata(self) -> bool:
        return os.path.exists(os.path.join(self.workspace.path, ".git"))

    def run_git(self, args: list) -> str:
        cmd_str = f"git {' '.join(args)}"
        decision = self.policy_engine.evaluate_shell_command(cmd_str)
        if not decision.allowed:
            return f"Error: Command blocked by policy: {decision.reason}"

        if self._is_read_only_git(args) and not self._has_git_metadata():
            logger.debug("Skipping git command outside repository: %s", cmd_str)
            return ""

        cache_key = None
        if self.cache and self.cache.allows_read_only_tools() and self._is_read_only_git(args):
            repo_snapshot_hash = (
                self.repo_snapshot_hash_getter()
                if callable(self.repo_snapshot_hash_getter)
                else "no-repo"
            )
            cache_key = self.cache.build_tool_key(
                tool="git",
                identifier=cmd_str,
                repo_snapshot_hash=repo_snapshot_hash,
                policy_hash=self.policy_hash,
            )
            cached = self.cache.get_json("tool", cache_key)
            if cached is not None:
                return str(cached)

        command = ["git"] + args
        logger.info(f"Running git command: {' '.join(command)}")
        result = subprocess.run(command, cwd=self.workspace.path, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Git command failed: {result.stderr}")
            return f"Error: {result.stderr}"
        if cache_key and self.cache:
            self.cache.set_json("tool", cache_key, result.stdout)
        return result.stdout
