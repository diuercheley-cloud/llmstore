# Owner: platform-operations
import os
from typing import Any, Dict
from app.compat.autogen.adapters import ConversableAgent, UserProxyAgent

def import_autogen_agent_from_source(source_code: str, target_variable: str = "assistant") -> Any:
    """
    Dynamically executes AutoGen source code and extracts the ConversableAgent/UserProxyAgent instance.
    """
    local_vars: Dict[str, Any] = {}
    global_vars = {
        "ConversableAgent": ConversableAgent,
        "UserProxyAgent": UserProxyAgent,
    }
    
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
