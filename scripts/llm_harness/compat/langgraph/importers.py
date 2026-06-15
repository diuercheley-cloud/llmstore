import logging
import os
from typing import Any

from ..base import BaseImporter, ImportResult
from .adapters import CompiledStateGraph, StateGraph

logger = logging.getLogger(__name__)

MAX_CODE_LENGTH = 100_000
BLOCKED_PATTERNS = [
    "__import__",
    "os.",
    "subprocess",
    "sys.",
    "import ",
    "open(",
    "eval(",
    "exec(",
    "__builtins__",
    "globals()",
    "locals()",
    "getattr",
    "setattr",
    "delattr",
    "compile",
    ".write(",
    ".read(",
    "socket",
    "ctypes",
    "threading",
    "multiprocessing",
    "signal",
    "shutil",
]


class LangGraphImporter(BaseImporter[Any]):
    def __init__(self, extra_globals: dict[str, Any] | None = None):
        self.extra_globals = extra_globals or {}

    def _build_globals(self) -> dict[str, Any]:
        return {
            "StateGraph": StateGraph,
            "CompiledStateGraph": CompiledStateGraph,
            **self.extra_globals,
        }

    def _validate_source(self, source_code: str):
        if len(source_code) > MAX_CODE_LENGTH:
            raise ValueError(f"Source code exceeds maximum length of {MAX_CODE_LENGTH}")
        for pattern in BLOCKED_PATTERNS:
            if pattern in source_code:
                raise ValueError(f"Source code contains blocked pattern: '{pattern}'")

    def from_source(
        self,
        source_code: str,
        target_variable: str = "graph",
    ) -> ImportResult[Any]:
        self._validate_source(source_code)
        local_vars: dict[str, Any] = {}
        global_vars = self._build_globals()

        logger.info("Executing LangGraph source code (len=%d)", len(source_code))
        try:
            exec(source_code, global_vars, local_vars)
        except Exception as e:
            return ImportResult(
                success=False,
                error=f"Failed to execute source code: {e}",
            )

        if target_variable in local_vars:
            return ImportResult(success=True, data=local_vars[target_variable])

        for val in local_vars.values():
            if isinstance(val, (StateGraph, CompiledStateGraph)):
                warnings = [
                    f"Target variable '{target_variable}' not found; using first graph instance."
                ]
                return ImportResult(success=True, data=val, warnings=warnings)

        return ImportResult(
            success=False,
            error=f"No StateGraph or CompiledStateGraph found. Expected variable '{target_variable}'.",
        )

    def from_file(
        self,
        file_path: str,
        target_variable: str = "graph",
    ) -> ImportResult[Any]:
        if not os.path.exists(file_path):
            return ImportResult(
                success=False,
                error=f"File not found: {file_path}",
            )

        try:
            with open(file_path, encoding="utf-8") as f:
                source_code = f.read()
        except OSError as e:
            return ImportResult(
                success=False,
                error=f"Failed to read file: {e}",
            )

        return self.from_source(source_code, target_variable)
