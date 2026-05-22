import httpx
from typing import Any, Dict
from app.services.agents.tool_adapter_contract import ToolAdapterContract
from app.core.config import get_settings


class HttpGetToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "http_get_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch."},
                "timeout": {"type": "integer", "default": 10}
            },
            "required": ["url"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status_code": {"type": "integer"},
                "content": {"type": "string"},
                "headers": {"type": "object"}
            }
        }

    @property
    def side_effect_level(self) -> str:
        return "external"

    def to_registry_dict(self) -> Dict[str, Any]:
        data = super().to_registry_dict()
        data["data_boundary"] = "internet"
        data["category"] = "external_api"
        return data

    async def execute(self, **kwargs) -> Dict[str, Any]:
        settings = get_settings()
        if not getattr(settings, "agent_http_tool_enabled", False):
            raise ValueError("HTTP tool is disabled by feature flag.")

        url = kwargs["url"]
        timeout = kwargs.get("timeout", 10)

        # Basic security: avoid internal IP addresses or secrets (placeholder logic)
        if "169.254.169.254" in url:
             raise ValueError("Access to metadata service is prohibited.")

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            return {
                "status_code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers)
            }

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would fetch {kwargs['url']}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "External GET side effects cannot be automatically rolled back."}

    async def healthcheck(self) -> bool:
        return True
