import asyncio
from typing import Any, Dict
from app.services.agents.tool_adapter_contract import ToolAdapterContract
from app.core.config import get_settings


class ShellCommandToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "shell_command_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "args": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["command"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "exit_code": {"type": "integer"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "destructive"

    def to_registry_dict(self) -> Dict[str, Any]:
        data = super().to_registry_dict()
        data["category"] = "shell_command"
        data["enabled"] = False
        return data

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_shell_tool_enabled", False):
             raise ValueError("Shell tool is disabled by feature flag.")

        command = kwargs["command"]
        args = [str(arg) for arg in kwargs.get("args", [])]
        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode
        }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would execute shell command: {kwargs['command']}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Shell command effects cannot be automatically rolled back."}

    async def healthcheck(self) -> bool:
        return True
