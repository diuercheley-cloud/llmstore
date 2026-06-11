# Owner: platform-operations
import importlib.util
import os
import sys
from typing import Any, Dict
from app.compat.langgraph.adapters import StateGraph, CompiledStateGraph

def import_langgraph_from_source(source_code: str, target_variable: str = "graph") -> Any:
    """
    Dynamically executes LangGraph source code and extracts the StateGraph or CompiledStateGraph.
    """
    local_vars: Dict[str, Any] = {}
    # Provide the mock StateGraph and CompiledStateGraph in the execution context
    global_vars = {
        "StateGraph": StateGraph,
        "CompiledStateGraph": CompiledStateGraph,
    }
    
    exec(source_code, global_vars, local_vars)
    
    if target_variable in local_vars:
        return local_vars[target_variable]
        
    # Fallback: look for any instance of StateGraph/CompiledStateGraph
    for val in local_vars.values():
        if isinstance(val, (StateGraph, CompiledStateGraph)):
            return val
            
    raise ValueError(f"No StateGraph or CompiledStateGraph found in the source code. Expected '{target_variable}'.")

def import_langgraph_from_file(file_path: str, target_variable: str = "graph") -> Any:
    """
    Loads a python file and extracts the StateGraph or CompiledStateGraph.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
        
    return import_langgraph_from_source(source_code, target_variable)
