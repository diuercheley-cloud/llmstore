# Owner: platform-operations
import os
from typing import Any, Dict
from app.compat.crewai.adapters import Agent, Task, Crew

def import_crew_from_source(source_code: str, target_variable: str = "crew") -> Any:
    """
    Dynamically executes CrewAI source code and extracts the Crew instance.
    """
    local_vars: Dict[str, Any] = {}
    global_vars = {
        "Agent": Agent,
        "Task": Task,
        "Crew": Crew,
    }
    
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
        
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
        
    return import_crew_from_source(source_code, target_variable)
