from typing import Any, Dict

import httpx
from app.core.config import get_settings
from app.services.agents.browser.browser_policy import check_browser_url_policy
from app.services.agents.tool_adapter_contract import ToolAdapterContract


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
        
        # Apply the same DNS-aware SSRF policy used by the browser tool.
        try:
            check_browser_url_policy(url, check_feature_flags=False)
        except ValueError as exc:
            raise ValueError("Access to metadata or internal services is strictly prohibited.") from exc

        # 2. Domain Allowlist (optional but recommended)
        # For this stack, let's assume we allow everything NOT internal unless a specific list exists
        
        async with httpx.AsyncClient() as client:
            # 3. Method Allowlist
            method = kwargs.get("method", "GET").upper()
            if method not in ("GET", "HEAD"):
                raise ValueError(f"HTTP method '{method}' is not allowed in this tool.")

            try:
                response = await client.request(method, url, timeout=timeout)
                # 4. Response Size Limit
                content = response.text
                if len(content) > 500000: # 500KB limit
                    content = content[:500000] + "... [TRUNCATED]"
                
                return {
                    "status_code": response.status_code,
                    "content": content,
                    "headers": {k: v for k, v in response.headers.items() if "auth" not in k.lower() and "key" not in k.lower()}
                }
            except Exception as e:
                return {"error": str(e), "status_code": -1}

    async def dry_run(self, **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run", "message": f"Would fetch {kwargs['url']}"}

    async def rollback(self, invocation_id: str, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "message": "External GET side effects cannot be automatically rolled back."}

    async def healthcheck(self) -> bool:
        return True
