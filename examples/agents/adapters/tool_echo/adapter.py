from typing import Any, Dict, Tuple
from kleberai.agents.adapters import ToolAdapterV1, AdapterManifest

class EchoTool(ToolAdapterV1):
    async def manifest(self) -> AdapterManifest:
        return AdapterManifest(
            id="echo-tool",
            name="Echo Tool",
            version="1.0.0",
            compatibility_version="v1",
            description="Simple tool that returns input as-is.",
            permissions=["execute"]
        )

    async def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }

    async def healthcheck(self) -> bool:
        return True

    async def dry_run(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "message" not in params:
            return False, "Missing 'message' field"
        return True, "Valid input"

    async def execute(self, tool_input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"output": tool_input.get("message", "")}
