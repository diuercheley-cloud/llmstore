import logging
import os

from ..cache import LocalCache

logger = logging.getLogger(__name__)


class FileTools:
    """
    Governed filesystem tools for agents.
    """

    def __init__(
        self,
        workspace,
        policy_engine=None,
        cache: LocalCache | None = None,
        repo_snapshot_hash_getter=None,
        policy_hash: str = "",
    ):
        self.workspace = workspace
        self.policy_engine = policy_engine
        self.cache = cache
        self.repo_snapshot_hash_getter = repo_snapshot_hash_getter
        self.policy_hash = policy_hash

    def _validate_path(self, path: str):
        if not self.policy_engine:
            return

        decision = self.policy_engine.evaluate_file_path(path)
        if not decision.allowed:
            raise PermissionError(decision.reason or "Path blocked by policy")

    def list_files(self, path: str = ".") -> list[str]:
        self._validate_path(path)
        if self.cache and self.cache.allows_read_only_tools():
            repo_snapshot_hash = (
                self.repo_snapshot_hash_getter()
                if callable(self.repo_snapshot_hash_getter)
                else "no-repo"
            )
            cache_key = self.cache.build_tool_key(
                tool="list_files",
                identifier=path,
                repo_snapshot_hash=repo_snapshot_hash,
                policy_hash=self.policy_hash,
            )
            cached = self.cache.get_json("tool", cache_key)
            if cached is not None:
                return list(cached)
        full_path = self.workspace.get_path(path)
        result = os.listdir(full_path)
        if self.cache and self.cache.allows_read_only_tools():
            self.cache.set_json("tool", cache_key, result)
        return result

    def read_file(self, filename: str) -> str:
        self._validate_path(filename)
        return self.workspace.read_file(filename)

    def write_file(self, filename: str, content: str):
        self._validate_path(filename)
        return self.workspace.write_file(filename, content)
