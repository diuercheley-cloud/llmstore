from typing import Any

from app.services.agents.tool_adapter_contract import ToolAdapterContract


class EchoToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "echo_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "The message to echo."}},
            "required": ["message"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"echo": {"type": "string"}}}

    @property
    def side_effect_level(self) -> str:
        return "none"

    async def execute(self, **kwargs) -> dict[str, Any]:
        return {"echo": kwargs.get("message", "")}

    async def dry_run(self, **kwargs) -> dict[str, Any]:
        return await self.execute(**kwargs)

    async def rollback(self, invocation_id: str, **kwargs) -> dict[str, Any]:
        return {"status": "success", "message": "No side effects to rollback for echo_tool."}

    async def healthcheck(self) -> bool:
        return True
