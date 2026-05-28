# Owner: Platform Operations
from typing import Any, Dict, List, Optional
from app.services.agents.connectors.base import (
    ConnectorAdapter,
    ConnectorCapability,
    RiskLevel,
    SideEffectLevel,
)
from app.services.agents.connectors.connector_runtime import ConnectorRuntime
from app.services.agents.connectors.connector_mode import ConnectorMode
from app.services.agents.connectors.http_client import ConnectorHTTPClient

class SlackConnector(ConnectorAdapter):
    @property
    def connector_name(self) -> str:
        return "slack"

    @property
    def mode(self) -> ConnectorMode:
        return ConnectorRuntime.get_mode(self.connector_name)

    @property
    def connector_version(self) -> str:
        return "1.1.0"

    @property
    def provider(self) -> str:
        return "Slack"

    @property
    def capabilities(self) -> List[ConnectorCapability]:
        return [
            ConnectorCapability.SEARCH,
            ConnectorCapability.WRITE,
            ConnectorCapability.COMMENT,
            ConnectorCapability.READ
        ]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["search_messages", "post_message", "create_thread_reply", "list_channels"]},
                "params": {"type": "object"}
            },
            "required": ["action"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    @property
    def required_scopes(self) -> List[str]:
        return ["chat:write", "search:read", "channels:history", "channels:read"]

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    @property
    def side_effect_level(self) -> SideEffectLevel:
        return SideEffectLevel.EXTERNAL

    @property
    def rate_limit_policy(self) -> Dict[str, Any]:
        return {"requests_per_minute": 50}

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
            "search_messages": ConnectorCapability.SEARCH,
            "post_message": ConnectorCapability.WRITE,
            "create_thread_reply": ConnectorCapability.COMMENT,
            "list_channels": ConnectorCapability.READ
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
            return self._with_execution_metadata(
                await self._execute_real(action, params, credentials),
                mode="real",
            )
        return await self._execute_mock(action, params)

    async def _execute_real(self, action: str, params: Dict[str, Any], credentials: Dict[str, Any]) -> Dict[str, Any]:
        ConnectorRuntime.ensure_real_allowed(self.connector_name)
        ConnectorRuntime.validate_credentials(self.connector_name, credentials)

        token = credentials.get("token") or credentials.get("api_key")
        client = ConnectorHTTPClient(
            base_url="https://slack.com/api",
            headers={"Authorization": f"Bearer {token}"}
        )

        if action == "list_channels":
            return await client.request("GET", "conversations.list")

        elif action == "post_message":
            channel = params.get("channel")
            text = params.get("text")
            if not channel or not text:
                raise ValueError("channel and text are required for post_message")
            return await client.request("POST", "chat.postMessage", json_data={"channel": channel, "text": text})

        elif action == "search_messages":
            query = params.get("query")
            if not query:
                raise ValueError("query is required for search_messages")
            return await client.request("GET", "search.messages", params={"query": query})

        elif action == "create_thread_reply":
            channel = params.get("channel")
            thread_ts = params.get("thread_ts")
            text = params.get("text")
            if not channel or not thread_ts or not text:
                raise ValueError("channel, thread_ts, and text are required for create_thread_reply")
            return await client.request("POST", "chat.postMessage", json_data={"channel": channel, "thread_ts": thread_ts, "text": text})

        raise self._unsupported_action(
            action,
            mode="real",
            supported_actions=["create_thread_reply", "list_channels", "post_message", "search_messages"],
        )

    async def _execute_mock(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "search_messages":
            return self._with_execution_metadata(
                {"messages": [{"text": "Hello world", "user": "U12345"}]},
                mode="mock",
            )
        elif action == "post_message":
            return self._with_execution_metadata(
                {"status": "success", "ts": "1234567890.123456"},
                mode="mock",
            )
        elif action == "create_thread_reply":
            return self._with_execution_metadata(
                {"status": "success", "ts": "1234567890.789012"},
                mode="mock",
            )
        elif action == "list_channels":
            return self._with_execution_metadata(
                {"channels": [{"id": "C123", "name": "general"}]},
                mode="mock",
            )
            
        raise self._unsupported_action(
            action,
            mode="mock",
            supported_actions=["create_thread_reply", "list_channels", "post_message", "search_messages"],
        )
