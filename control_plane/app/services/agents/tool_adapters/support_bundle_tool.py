from typing import Any, Dict

from app.services.agents.tool_adapter_contract import ToolAdapterContract


class SupportBundleToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "support_bundle_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "include_logs": {"type": "boolean", "default": True}
            },
            "required": ["ticket_id"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bundle_url": {"type": "string"},
                "bundle_id": {"type": "string"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "write"

    async def execute(self, **kwargs) -> Dict[str, Any]:
        return {
            "bundle_url": f"https://support.example.com/bundles/{kwargs['ticket_id']}_bundle.tar.gz",
            "bundle_id": "sb-12345"
        }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would create support bundle for ticket {kwargs['ticket_id']}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "Support bundle deleted."}

    async def healthcheck(self) -> bool:
        return True
