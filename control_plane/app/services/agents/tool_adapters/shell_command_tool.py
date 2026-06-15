import asyncio
from typing import Any

from app.core.config import get_settings
from app.services.agents.tool_adapter_contract import ToolAdapterContract


class ShellCommandToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "shell_command_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "args": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["command"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
                "exit_code": {"type": "integer"},
            },
        }

    @property
    def side_effect_level(self) -> str:
        return "destructive"

    def to_registry_dict(self) -> dict[str, Any]:
        data = super().to_registry_dict()
        data["category"] = "shell_command"
        data["enabled"] = False
        return data

    async def execute(self, **kwargs) -> dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_shell_tool_enabled", False):
            raise ValueError("Shell tool is disabled by feature flag.")

        command = kwargs["command"]
        args = [str(arg) for arg in kwargs.get("args", [])]

        # 1. Command Allowlist
        allowlist = {"ls", "grep", "cat", "echo", "ps", "pwd", "whoami", "df", "free"}
        if command not in allowlist:
            raise ValueError(f"Command '{command}' is not in the allowed shell command list.")

        # 2. Block sensitive file access in args
        sensitive_patterns = {
            ".env",
            "data/pki",
            "uploads/",
            "models/",
            "/etc/passwd",
            "/etc/shadow",
            ".ssh/",
        }
        for arg in args:
            if any(p in arg for p in sensitive_patterns):
                raise ValueError(f"Access to sensitive path detected in arguments: {arg}")

        # 3. Execution with Timeout
        timeout = kwargs.get("timeout_seconds", 5)
        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    command,
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=False,  # Mandatory security: no shell expansion
                ),
                timeout=float(timeout),
            )
            stdout, stderr = await proc.communicate()

            # Sanitization/Truncation
            decoded_out = stdout.decode("utf-8", errors="replace")[:10000]
            decoded_err = stderr.decode("utf-8", errors="replace")[:2000]

            return {
                "stdout": decoded_out,
                "stderr": decoded_err,
                "exit_code": proc.returncode,
                "truncated": len(stdout) > 10000,
            }
        except TimeoutError:
            return {"error": "Execution timed out", "exit_code": -1}
        except Exception as e:
            return {"error": str(e), "exit_code": -1}

    async def dry_run(self, **kwargs) -> dict[str, Any]:
        return {"status": "dry_run", "message": f"Would execute shell command: {kwargs['command']}"}

    async def rollback(self, invocation_id: str, **kwargs) -> dict[str, Any]:
        return {
            "status": "success",
            "message": "Shell command effects cannot be automatically rolled back.",
        }

    async def healthcheck(self) -> bool:
        return True
