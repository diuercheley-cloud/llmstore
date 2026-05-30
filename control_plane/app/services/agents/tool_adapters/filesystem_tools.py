# Owner: agent-platform
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from app.services.agents.tool_adapter_contract import ToolAdapterContract
from app.core.config import get_settings


def _resolve_and_verify_path(requested_path: str, tenant_id: str) -> Path:
    settings = get_settings()
    workspace_root = Path(settings.web_ide_workspaces_dir).resolve() / tenant_id
    workspace_root.mkdir(parents=True, exist_ok=True)
    
    # Strip leading slash to ensure we treat it as relative to the workspace
    rel_path = requested_path.lstrip("/")
    combined = workspace_root / rel_path
    
    try:
        resolved = combined.resolve()
    except Exception as e:
        raise ValueError(f"Invalid path: {e}")
        
    # Check path traversal and symlink escape
    if not resolved.is_relative_to(workspace_root):
        raise ValueError("Access denied: path traversal or symlink escape detected.")
        
    # Check sensitive files
    path_str = str(resolved).lower()
    req_path_str = requested_path.lower()
    
    blocked_patterns = [
        ".env",
        "keys",
        "certs",
        "pki",
        "docker.sock",
        "model",
    ]
    # Check extensions for model files
    blocked_exts = {".bin", ".pt", ".onnx", ".gguf", ".safetensors"}
    
    if resolved.suffix.lower() in blocked_exts:
        raise ValueError("Access to model files is prohibited.")
        
    if any(p in path_str or p in req_path_str for p in blocked_patterns):
        raise ValueError("Access to sensitive/blocked file pattern is prohibited.")
        
    return resolved


def _generate_receipt(
    tenant_id: str,
    agent_id: Any,
    operation: str,
    path: str,
    status: str = "success",
    additional_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).isoformat()
    receipt_body = {
        "tenant_id": tenant_id,
        "agent_id": str(agent_id) if agent_id else "none",
        "operation": operation,
        "path": path,
        "status": status,
        "timestamp": timestamp,
        "additional_info": additional_info or {}
    }
    
    import json
    serialized = json.dumps(receipt_body, sort_keys=True)
    receipt_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    
    return {
        "body": receipt_body,
        "hash": receipt_hash,
        "signature": f"fs_receipt_sig_{receipt_hash[:16]}"
    }


class ReadFileToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file relative to the workspace."},
                "encoding": {"type": "string", "default": "utf-8", "description": "Encoding to use when reading the file."}
            },
            "required": ["path"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "receipt": {"type": "object"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "read"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_file_tools_enabled", False):
            raise ValueError("Agent file tools are disabled by feature flag.")

        tenant_id = kwargs.get("tenant_id", "default")
        agent_id = kwargs.get("agent_id")
        path_str = kwargs["path"]
        encoding = kwargs.get("encoding", "utf-8")

        resolved_path = _resolve_and_verify_path(path_str, tenant_id)

        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {path_str}")
        if not resolved_path.is_file():
            raise ValueError(f"Path is not a file: {path_str}")

        try:
            with open(resolved_path, "r", encoding=encoding) as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read file: {e}")

        receipt = _generate_receipt(tenant_id, agent_id, "read_file", path_str, "success")
        return {
            "content": content,
            "receipt": receipt
        }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would read file: {kwargs.get('path')}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Read operation has no rollback."}

    async def healthcheck(self) -> bool:
        return True


class WriteFileToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file relative to the workspace."},
                "content": {"type": "string", "description": "Content to write to the file."},
                "encoding": {"type": "string", "default": "utf-8", "description": "Encoding to use when writing the file."}
            },
            "required": ["path", "content"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "written_bytes": {"type": "integer"},
                "receipt": {"type": "object"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "write"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_file_tools_enabled", False):
            raise ValueError("Agent file tools are disabled by feature flag.")
        if not getattr(settings, "agent_file_write_enabled", False):
            raise ValueError("Agent file write tool is disabled by feature flag.")

        tenant_id = kwargs.get("tenant_id", "default")
        agent_id = kwargs.get("agent_id")
        path_str = kwargs["path"]
        content = kwargs["content"]
        encoding = kwargs.get("encoding", "utf-8")

        resolved_path = _resolve_and_verify_path(path_str, tenant_id)

        # Ensure parent directories exist
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(resolved_path, "w", encoding=encoding) as f:
                written = f.write(content)
        except Exception as e:
            raise ValueError(f"Failed to write file: {e}")

        content_hash = hashlib.sha256(content.encode(encoding, errors="replace")).hexdigest()
        receipt = _generate_receipt(
            tenant_id, agent_id, "write_file", path_str, "success",
            additional_info={"written_bytes": written, "content_hash": content_hash}
        )
        return {
            "success": True,
            "written_bytes": written,
            "receipt": receipt
        }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would write to file: {kwargs.get('path')}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "File write operation cannot be automatically rolled back."}

    async def healthcheck(self) -> bool:
        return True


class ListDirectoryToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "", "description": "Directory path relative to the workspace root."}
            }
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "size": {"type": "integer"},
                            "last_modified": {"type": "string"}
                        }
                    }
                },
                "receipt": {"type": "object"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "read"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_file_tools_enabled", False):
            raise ValueError("Agent file tools are disabled by feature flag.")

        tenant_id = kwargs.get("tenant_id", "default")
        agent_id = kwargs.get("agent_id")
        path_str = kwargs.get("path", "")

        resolved_path = _resolve_and_verify_path(path_str, tenant_id)

        if not resolved_path.exists():
            raise FileNotFoundError(f"Directory not found: {path_str}")
        if not resolved_path.is_dir():
            raise ValueError(f"Path is not a directory: {path_str}")

        entries = []
        try:
            for entry in os.scandir(resolved_path):
                entry_name = entry.name.lower()
                blocked_patterns = [".env", "keys", "certs", "pki", "docker.sock", "model"]
                blocked_exts = {".bin", ".pt", ".onnx", ".gguf", ".safetensors"}
                
                if any(p in entry_name for p in blocked_patterns):
                    continue
                if Path(entry.path).suffix.lower() in blocked_exts:
                    continue

                entry_type = "other"
                if entry.is_file():
                    entry_type = "file"
                elif entry.is_dir():
                    entry_type = "directory"
                elif entry.is_symlink():
                    entry_type = "symlink"

                try:
                    stat_info = entry.stat()
                    size = stat_info.st_size if entry.is_file() else 0
                    last_mod = datetime.fromtimestamp(stat_info.st_mtime, timezone.utc).isoformat()
                except Exception:
                    size = 0
                    last_mod = "unknown"

                entries.append({
                    "name": entry.name,
                    "type": entry_type,
                    "size": size,
                    "last_modified": last_mod
                })
        except Exception as e:
            raise ValueError(f"Failed to list directory: {e}")

        receipt = _generate_receipt(tenant_id, agent_id, "list_directory", path_str, "success")
        return {
            "entries": entries,
            "receipt": receipt
        }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would list directory: {kwargs.get('path', '')}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "List directory operation has no rollback."}

    async def healthcheck(self) -> bool:
        return True


class DeleteFileToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "delete_file"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file relative to the workspace."}
            },
            "required": ["path"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "receipt": {"type": "object"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "destructive"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_file_tools_enabled", False):
            raise ValueError("Agent file tools are disabled by feature flag.")
        if not getattr(settings, "agent_file_delete_enabled", False):
            raise ValueError("Agent file delete tool is disabled by feature flag.")

        tenant_id = kwargs.get("tenant_id", "default")
        agent_id = kwargs.get("agent_id")
        path_str = kwargs["path"]

        resolved_path = _resolve_and_verify_path(path_str, tenant_id)

        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {path_str}")
        if not resolved_path.is_file():
            raise ValueError(f"Path is not a file: {path_str}")

        try:
            os.remove(resolved_path)
        except Exception as e:
            raise ValueError(f"Failed to delete file: {e}")

        receipt = _generate_receipt(tenant_id, agent_id, "delete_file", path_str, "success")
        return {
            "success": True,
            "receipt": receipt
        }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would delete file: {kwargs.get('path')}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Delete operation cannot be automatically rolled back."}

    async def healthcheck(self) -> bool:
        return True


class StatFileToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "stat_file"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file or directory relative to the workspace."}
            },
            "required": ["path"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "exists": {"type": "boolean"},
                "size": {"type": "integer"},
                "type": {"type": "string"},
                "last_modified": {"type": "string"},
                "receipt": {"type": "object"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "read"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_file_tools_enabled", False):
            raise ValueError("Agent file tools are disabled by feature flag.")

        tenant_id = kwargs.get("tenant_id", "default")
        agent_id = kwargs.get("agent_id")
        path_str = kwargs["path"]

        resolved_path = _resolve_and_verify_path(path_str, tenant_id)

        if not resolved_path.exists():
            receipt = _generate_receipt(tenant_id, agent_id, "stat_file", path_str, "success", {"exists": False})
            return {
                "exists": False,
                "size": 0,
                "type": "none",
                "last_modified": "none",
                "receipt": receipt
            }

        entry_type = "other"
        if resolved_path.is_file():
            entry_type = "file"
        elif resolved_path.is_dir():
            entry_type = "directory"
        elif resolved_path.is_symlink():
            entry_type = "symlink"

        try:
            stat_info = resolved_path.stat()
            size = stat_info.st_size if resolved_path.is_file() else 0
            last_mod = datetime.fromtimestamp(stat_info.st_mtime, timezone.utc).isoformat()
        except Exception as e:
            raise ValueError(f"Failed to get stat for file: {e}")

        receipt = _generate_receipt(
            tenant_id, agent_id, "stat_file", path_str, "success",
            {"exists": True, "type": entry_type, "size": size}
        )
        return {
            "exists": True,
            "size": size,
            "type": entry_type,
            "last_modified": last_mod,
            "receipt": receipt
        }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would stat path: {kwargs.get('path')}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Stat operation has no rollback."}

    async def healthcheck(self) -> bool:
        return True
