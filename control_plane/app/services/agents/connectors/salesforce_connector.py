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

class SalesforceConnector(ConnectorAdapter):
    @property
    def connector_name(self) -> str:
        return "salesforce"

    @property
    def mode(self) -> ConnectorMode:
        return ConnectorRuntime.get_mode(self.connector_name)

    @property
    def connector_version(self) -> str:
        return "1.1.0"

    @property
    def provider(self) -> str:
        return "Salesforce"

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
                "action": {"type": "string", "enum": ["search_accounts", "get_account", "create_task"]},
                "params": {"type": "object"}
            },
            "required": ["action"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    @property
    def required_scopes(self) -> List[str]:
        return ["api", "refresh_token"]

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.HIGH

    @property
    def side_effect_level(self) -> SideEffectLevel:
        return SideEffectLevel.EXTERNAL

    @property
    def rate_limit_policy(self) -> Dict[str, Any]:
        return {"requests_per_minute": 100}

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
            "search_accounts": ConnectorCapability.SEARCH,
            "get_account": ConnectorCapability.READ,
            "create_task": ConnectorCapability.CREATE
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

        instance_url = credentials.get("instance_url")
        token = credentials.get("token") or credentials.get("api_key")
        if not instance_url or not token:
            raise ValueError("instance_url and token are required for Salesforce real mode")

        client = ConnectorHTTPClient(
            base_url=instance_url,
            headers={"Authorization": f"Bearer {token}"}
        )

        if action == "get_account":
            account_id = params.get("account_id")
            if not account_id:
                raise ValueError("account_id is required for get_account")
            return await client.request("GET", f"/services/data/v60.0/sobjects/Account/{account_id}")
        elif action == "search_accounts":
            q = params.get("q")
            if not q:
                raise ValueError("q is required for search_accounts")
            # SOSL or SOQL
            return await client.request("GET", "/services/data/v60.0/query", params={"q": f"SELECT Id, Name FROM Account WHERE Name LIKE '%{q}%'"})
        elif action == "create_task":
            subject = params.get("subject")
            if not subject:
                raise ValueError("subject is required for create_task")
            payload = {
                "Subject": subject,
                "Status": params.get("status", "Not Started"),
            }
            if params.get("description"):
                payload["Description"] = params["description"]
            if params.get("account_id"):
                payload["WhatId"] = params["account_id"]
            if params.get("owner_id"):
                payload["OwnerId"] = params["owner_id"]
            return await client.request("POST", "/services/data/v60.0/sobjects/Task", json_data=payload)

        raise self._unsupported_action(
            action,
            mode="real",
            supported_actions=["create_task", "get_account", "search_accounts"],
        )

    async def _execute_mock(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "search_accounts":
            return self._with_execution_metadata(
                {"accounts": [{"id": "ACC1", "name": "Acme Corp"}]},
                mode="mock",
            )
        elif action == "get_account":
            return self._with_execution_metadata(
                {"account": {"id": params.get("account_id"), "name": "Mock Account", "industry": "Software"}},
                mode="mock",
            )
        elif action == "create_task":
            return self._with_execution_metadata(
                {"status": "success", "task_id": "TSK123"},
                mode="mock",
            )
            
        raise self._unsupported_action(
            action,
            mode="mock",
            supported_actions=["create_task", "get_account", "search_accounts"],
        )
