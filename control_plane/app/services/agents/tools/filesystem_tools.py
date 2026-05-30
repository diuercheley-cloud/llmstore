# Owner: agent-platform
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Base directory for agent file operations (sandbox)
AGENT_SANDBOX_DIR = os.environ.get("AGENT_SANDBOX_DIR", "/tmp/agent_sandbox")

def _ensure_sandbox():
    if not os.path.exists(AGENT_SANDBOX_DIR):
        os.makedirs(AGENT_SANDBOX_DIR, exist_ok=True)

def _secure_path(path: str) -> str:
    """Ensures the path is within the sandbox."""
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or os.path.isabs(path):
        # We handle absolute paths by joining them to sandbox
        path = path.lstrip("/")
        
    full_path = os.path.join(AGENT_SANDBOX_DIR, path)
    
    # Final check
    if not os.path.abspath(full_path).startswith(os.path.abspath(AGENT_SANDBOX_DIR)):
        raise ValueError(f"Path traversal detected: {path}")
        
    return full_path

async def list_directory(directory: str = ".") -> Dict[str, Any]:
    """Lists files and folders in a directory within the sandbox."""
    _ensure_sandbox()
    try:
        secure_dir = _secure_path(directory)
        if not os.path.exists(secure_dir):
            return {"status": "error", "message": f"Directory not found: {directory}"}
        
        items = os.listdir(secure_dir)
        result = []
        for item in items:
            full = os.path.join(secure_dir, item)
            result.append({
                "name": item,
                "type": "directory" if os.path.isdir(full) else "file",
                "size": os.path.getsize(full) if os.path.isfile(full) else None
            })
        return {"status": "success", "items": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def read_file(file_path: str) -> Dict[str, Any]:
    """Reads the content of a file within the sandbox."""
    _ensure_sandbox()
    try:
        secure_file = _secure_path(file_path)
        if not os.path.exists(secure_file):
            return {"status": "error", "message": f"File not found: {file_path}"}
        
        with open(secure_file, "r") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Writes content to a file within the sandbox."""
    _ensure_sandbox()
    try:
        secure_file = _secure_path(file_path)
        # Ensure parent directories exist
        os.makedirs(os.path.dirname(secure_file), exist_ok=True)
        
        with open(secure_file, "w") as f:
            f.write(content)
        return {"status": "success", "message": f"File written successfully to {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def delete_file(file_path: str) -> Dict[str, Any]:
    """Deletes a file within the sandbox."""
    _ensure_sandbox()
    try:
        secure_file = _secure_path(file_path)
        if os.path.exists(secure_file):
            os.remove(secure_file)
            return {"status": "success", "message": f"File {file_path} deleted."}
        return {"status": "error", "message": "File not found."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
