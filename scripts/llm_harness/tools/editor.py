import logging

logger = logging.getLogger(__name__)

class EditorTools:
    def __init__(self, workspace, policy_engine=None):
        self.workspace = workspace
        self.policy_engine = policy_engine

    def _validate_path(self, path: str):
        if self.policy_engine:
            decision = self.policy_engine.evaluate_file_path(path)
            if not decision.allowed:
                raise PermissionError(decision.reason or "Path blocked by policy")

    def find_replace(self, filename: str, find_str: str, replace_str: str) -> bool:
        self._validate_path(filename)
        content = self.workspace.read_file(filename)
        if find_str not in content:
            return False

        new_content = content.replace(find_str, replace_str)
        self.workspace.write_file(filename, new_content)
        return True

    def insert_after(self, filename: str, anchor: str, content_to_insert: str) -> bool:
        self._validate_path(filename)
        content = self.workspace.read_file(filename)
        if anchor not in content:
            return False

        parts = content.split(anchor, 1)
        new_content = parts[0] + anchor + content_to_insert + parts[1]
        self.workspace.write_file(filename, new_content)
        return True

    def insert_before(self, filename: str, anchor: str, content_to_insert: str) -> bool:
        self._validate_path(filename)
        content = self.workspace.read_file(filename)
        if anchor not in content:
            return False

        parts = content.split(anchor, 1)
        new_content = parts[0] + content_to_insert + anchor + parts[1]
        self.workspace.write_file(filename, new_content)
        return True
