# Owner: Platform Operations
from typing import Any, Dict, List

from app.services.agents.connectors.base import (
    ConnectorAdapter,
    ConnectorCapability,
    RiskLevel,
    SideEffectLevel,
)
from app.services.agents.connectors.connector_mode import ConnectorMode
from app.services.agents.connectors.connector_runtime import ConnectorRuntime
from app.services.agents.connectors.http_client import ConnectorHTTPClient


class ConfluenceConnector(ConnectorAdapter):
    @property
    def connector_name(self) -> str:
        return "confluence"

    @property
    def mode(self) -> ConnectorMode:
        return ConnectorRuntime.get_mode(self.connector_name)

    @property
    def connector_version(self) -> str:
        return "1.1.0"

    @property
    def provider(self) -> str:
        return "Atlassian"

    @property
    def capabilities(self) -> List[ConnectorCapability]:
        return [
            ConnectorCapability.SEARCH,
            ConnectorCapability.READ,
            ConnectorCapability.CREATE
        ]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["search_pages", "get_page", "create_page"]},
                "params": {"type": "object"}
            },
            "required": ["action"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    @property
    def required_scopes(self) -> List[str]:
        return ["read:confluence-content.summary", "write:confluence-content"]

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.HIGH

    @property
    def side_effect_level(self) -> SideEffectLevel:
        return SideEffectLevel.EXTERNAL

    @property
    def rate_limit_policy(self) -> Dict[str, Any]:
        return {"requests_per_minute": 500}

    async def healthcheck(self) -> bool:
        return True

    async def dry_run(self, tenant_id: str, credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        return self._with_execution_metadata(
            {"status": "dry_run_success", "action": kwargs.get("action")},
            mode="dry_run",
        )

    async def execute(self, tenant_id: str, credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action")
        params = kwargs.get("params", {})
        
        capability_map = {
            "search_pages": ConnectorCapability.SEARCH,
            "get_page": ConnectorCapability.READ,
            "create_page": ConnectorCapability.CREATE
        }
        
        capability = capability_map.get(action)
        if not capability:
            raise ValueError(f"Unknown action: {action}")
        
        self._check_feature_flags(capability)

        # Agent IAM Check
        await self.check_iam(tenant_id, credentials, action)

        # Audit event
        await self.audit_connector_call(tenant_id, credentials, action, {"params": params, "mode": self.mode})

        if self.mode == ConnectorMode.REAL:
            real_kwargs = kwargs.copy()
            real_kwargs.pop("action", None)
            real_kwargs.pop("params", None)
            return self._with_execution_metadata(
                await self._execute_real(action, params, credentials, tenant_id=tenant_id, **real_kwargs),
                mode="real",
            )
        return await self._execute_mock(action, params)

    async def _execute_real(self, action: str, params: Dict[str, Any], credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        tenant_id = kwargs.get("tenant_id")
        invocation_id = kwargs.get("invocation_id", "manual")
        
        ConnectorRuntime.ensure_real_allowed(self.connector_name)
        ConnectorRuntime.validate_credentials(self.connector_name, credentials)

        base_url = credentials.get("base_url")
        if not base_url:
            raise ValueError("base_url is required for Confluence real mode")

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if credentials.get("token"):
            headers["Authorization"] = f"Bearer {credentials['token']}"
        elif credentials.get("username") and credentials.get("password"):
            import base64
            auth_str = f"{credentials['username']}:{credentials['password']}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"

        client = ConnectorHTTPClient(
            base_url=base_url,
            tenant_id=tenant_id,
            connector_name=self.connector_name,
            rate_limit_policy=self.rate_limit_policy,
            headers=headers
        )

        if action == "get_page":
            page_id = params.get("page_id")
            if not page_id:
                raise ValueError("page_id is required for get_page")
            return await client.request("GET", f"/wiki/rest/api/content/{page_id}")
        elif action == "search_pages":
            cql = params.get("cql")
            if not cql:
                raise ValueError("cql is required for search_pages")
            return await client.request("GET", "/wiki/rest/api/content/search", params={"cql": cql})
        elif action == "create_page":
            # High-risk write path
            approval_kwargs = kwargs.copy()
            approval_kwargs.pop("tenant_id", None)
            await self._ensure_approval(tenant_id, action, self.risk_level, **approval_kwargs)
            idempotency_key = kwargs.get("idempotency_key") or invocation_id

            space_key = params.get("space_key")
            title = params.get("title")
            body = params.get("body")
            if not space_key or not title or not body:
                raise ValueError("space_key, title, and body are required for create_page")
            payload = {
                "type": "page",
                "title": title,
                "space": {"key": space_key},
                "body": {
                    "storage": {
                        "value": body,
                        "representation": "storage",
                    }
                },
            }
            if params.get("parent_id"):
                payload["ancestors"] = [{"id": params["parent_id"]}]
            
            result = await client.request(
                "POST", 
                "/wiki/rest/api/content", 
                json_data=payload,
                idempotency_key=idempotency_key
            )
            
            await self._register_receipt(tenant_id, result, invocation_id)
            return result

        raise self._unsupported_action(
            action,
            mode="real",
            supported_actions=["create_page", "get_page", "search_pages"],
        )

    async def _execute_mock(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "search_pages":
            return self._with_execution_metadata(
                {"pages": [{"id": "123", "title": "Design Doc"}]},
                mode="mock",
            )
        elif action == "get_page":
            return self._with_execution_metadata(
                {"page": {"id": params.get("page_id"), "title": "Mock Page", "content": "Body text"}},
                mode="mock",
            )
        elif action == "create_page":
            return self._with_execution_metadata(
                {"status": "success", "page_id": "456"},
                mode="mock",
            )
            
        raise self._unsupported_action(
            action,
            mode="mock",
            supported_actions=["create_page", "get_page", "search_pages"],
        )
