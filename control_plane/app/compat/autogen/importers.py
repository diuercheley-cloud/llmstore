# Owner: platform-operations
import logging
import os
from typing import Any, Dict
from app.compat.autogen.adapters import ConversableAgent, UserProxyAgent

logger = logging.getLogger(__name__)

MAX_CODE_LENGTH = 100_000
BLOCKED_PATTERNS = [
    "__import__", "os.", "subprocess", "sys.", "import ",
    "open(", "eval(", "exec(", "__builtins__", "globals()",
    "locals()", "getattr", "setattr", "delattr", "compile",
    ".write(", ".read(", "socket", "ctypes", "threading",
    "multiprocessing", "signal", "shutil",
]


def _validate_source(source_code: str):
    if len(source_code) > MAX_CODE_LENGTH:
        raise ValueError(f"Source code exceeds maximum length of {MAX_CODE_LENGTH}")
    for pattern in BLOCKED_PATTERNS:
        if pattern in source_code:
            raise ValueError(f"Source code contains blocked pattern: '{pattern}'")


def import_autogen_agent_from_source(source_code: str, target_variable: str = "assistant") -> Any:
    """
    Dynamically executes AutoGen source code and extracts the ConversableAgent/UserProxyAgent instance.
    """
    _validate_source(source_code)
    local_vars: Dict[str, Any] = {}
    global_vars = {
        "ConversableAgent": ConversableAgent,
        "UserProxyAgent": UserProxyAgent,
    }
    
    logger.info("Executing AutoGen source code (len=%d)", len(source_code))
    exec(source_code, global_vars, local_vars)
    
    if target_variable in local_vars:
        return local_vars[target_variable]
        
    for val in local_vars.values():
        if isinstance(val, ConversableAgent):
            return val
            
    raise ValueError(f"No ConversableAgent instance found in the source code. Expected '{target_variable}'.")

def import_autogen_agent_from_file(file_path: str, target_variable: str = "assistant") -> Any:
    """
    Loads a python file and extracts the ConversableAgent instance.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
        
    return import_autogen_agent_from_source(source_code, target_variable)
