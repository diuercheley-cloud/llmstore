import ast
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

class SearchTools:
    def __init__(self, workspace, policy_engine=None):
        self.workspace = workspace
        self.policy_engine = policy_engine

    def _validate_path(self, path: str):
        if self.policy_engine:
            decision = self.policy_engine.evaluate_file_path(path)
            if not decision.allowed:
                raise PermissionError(decision.reason or "Path blocked by policy")

    def grep(
        self, pattern: str, path: str = ".", regex: bool = False, recursive: bool = True
    ) -> list[dict[str, Any]]:
        self._validate_path(path)
        full_path = self.workspace.get_path(path)
        results = []

        try:
            compiled_pattern = re.compile(pattern) if regex else None

            if recursive:
                for root, _, files in os.walk(full_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.workspace.path)
                        if self.policy_engine:
                            decision = self.policy_engine.evaluate_file_path(rel_path)
                            if not decision.allowed:
                                continue
                        results.extend(self._search_in_file(file_path, pattern, compiled_pattern))
            else:
                for file in os.listdir(full_path):
                    file_path = os.path.join(full_path, file)
                    if os.path.isfile(file_path):
                        rel_path = os.path.relpath(file_path, self.workspace.path)
                        if self.policy_engine:
                            decision = self.policy_engine.evaluate_file_path(rel_path)
                            if not decision.allowed:
                                continue
                        results.extend(self._search_in_file(file_path, pattern, compiled_pattern))
        except Exception as e:
            logger.error(f"Grep failed: {e}")

        return results

    def _search_in_file(
        self, file_path: str, pattern: str, compiled_pattern: re.Pattern | None
    ) -> list[dict[str, Any]]:
        results = []
        rel_path = os.path.relpath(file_path, self.workspace.path)
        try:
            with open(file_path, errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    match = False
                    if compiled_pattern:
                        if compiled_pattern.search(line):
                            match = True
                    elif pattern in line:
                        match = True

                    if match:
                        results.append({
                            "path": rel_path,
                            "line": i,
                            "content": line.strip()
                        })
        except Exception:
            pass
        return results

    def ast_search(self, symbol_name: str, path: str = ".") -> list[dict[str, Any]]:
        self._validate_path(path)
        full_path = self.workspace.get_path(path)
        results = []

        for root, _, files in os.walk(full_path):
            for file in files:
                if not file.endswith(".py"):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.workspace.path)
                if self.policy_engine:
                    decision = self.policy_engine.evaluate_file_path(rel_path)
                    if not decision.allowed:
                        continue

                try:
                    with open(file_path) as f:
                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef):
                            if node.name == symbol_name:
                                results.append({
                                    "path": rel_path,
                                    "line": node.lineno,
                                    "type": type(node).__name__,
                                    "name": node.name
                                })
                except Exception:
                    pass
        return results
