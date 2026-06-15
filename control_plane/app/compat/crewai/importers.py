# Owner: platform-operations
import logging
import os
from typing import Any

from app.compat.crewai.adapters import Agent, Crew, Task

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


def _validate_source(source_code: str):
    if len(source_code) > MAX_CODE_LENGTH:
        raise ValueError(f"Source code exceeds maximum length of {MAX_CODE_LENGTH}")
    for pattern in BLOCKED_PATTERNS:
        if pattern in source_code:
            raise ValueError(f"Source code contains blocked pattern: '{pattern}'")


def import_crew_from_source(source_code: str, target_variable: str = "crew") -> Any:
    """
    Dynamically executes CrewAI source code and extracts the Crew instance.
    """
    _validate_source(source_code)
    local_vars: dict[str, Any] = {}
    global_vars = {
        "Agent": Agent,
        "Task": Task,
        "Crew": Crew,
    }

    logger.info("Executing CrewAI source code (len=%d)", len(source_code))
    exec(source_code, global_vars, local_vars)

    if target_variable in local_vars:
        return local_vars[target_variable]

    for val in local_vars.values():
        if isinstance(val, Crew):
            return val

    raise ValueError(f"No Crew instance found in the source code. Expected '{target_variable}'.")


def import_crew_from_file(file_path: str, target_variable: str = "crew") -> Any:
    """
    Loads a python file and extracts the Crew instance.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        source_code = f.read()

    return import_crew_from_source(source_code, target_variable)
