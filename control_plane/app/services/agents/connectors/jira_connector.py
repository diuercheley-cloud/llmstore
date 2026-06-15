# Owner: Platform Operations
from typing import Any

from app.services.agents.connectors.base import (
    ConnectorAdapter,
    ConnectorCapability,
    RiskLevel,
    SideEffectLevel,
)
from app.services.agents.connectors.connector_mode import ConnectorMode
from app.services.agents.connectors.connector_runtime import ConnectorRuntime
from app.services.agents.connectors.http_client import ConnectorHTTPClient


class JiraConnector(ConnectorAdapter):
    @property
    def connector_name(self) -> str:
        return "jira"

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
    def capabilities(self) -> list[ConnectorCapability]:
        return [
            ConnectorCapability.SEARCH,
            ConnectorCapability.READ,
            ConnectorCapability.COMMENT,
            ConnectorCapability.CREATE,
        ]

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search_issues", "get_issue", "add_comment", "create_issue"],
                },
                "params": {"type": "object"},
            },
            "required": ["action"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {"type": "object"}

    @property
    def required_scopes(self) -> list[str]:
        return ["read:jira-work", "write:jira-work"]

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.HIGH

    @property
    def side_effect_level(self) -> SideEffectLevel:
        return SideEffectLevel.EXTERNAL

    @property
    def rate_limit_policy(self) -> dict[str, Any]:
        return {"requests_per_minute": 1000}

    async def healthcheck(self) -> bool:
        return True

    async def dry_run(
        self, tenant_id: str, credentials: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        return self._with_execution_metadata(
            {"status": "dry_run_success", "action": kwargs.get("action")},
            mode="dry_run",
        )

    async def execute(
        self, tenant_id: str, credentials: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        action = kwargs.get("action")
        params = kwargs.get("params", {})

        capability_map = {
            "search_issues": ConnectorCapability.SEARCH,
            "get_issue": ConnectorCapability.READ,
            "add_comment": ConnectorCapability.COMMENT,
            "create_issue": ConnectorCapability.CREATE,
        }

        capability = capability_map.get(action)
        if not capability:
            raise ValueError(f"Unknown action: {action}")

        self._check_feature_flags(capability)

        # Agent IAM Check
        await self.check_iam(tenant_id, credentials, action)

        # Audit event
        await self.audit_connector_call(
            tenant_id, credentials, action, {"params": params, "mode": self.mode}
        )

        if self.mode == ConnectorMode.REAL:
            real_kwargs = kwargs.copy()
            real_kwargs.pop("action", None)
            real_kwargs.pop("params", None)
            return self._with_execution_metadata(
                await self._execute_real(
                    action, params, credentials, tenant_id=tenant_id, **real_kwargs
                ),
                mode="real",
            )
        return await self._execute_mock(action, params)

    async def _execute_real(
        self, action: str, params: dict[str, Any], credentials: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        tenant_id = kwargs.get("tenant_id")
        invocation_id = kwargs.get("invocation_id", "manual")

        ConnectorRuntime.ensure_real_allowed(self.connector_name)
        ConnectorRuntime.validate_credentials(self.connector_name, credentials)

        base_url = credentials.get("base_url")
        if not base_url:
            raise ValueError(
                "base_url (Jira instance URL) is required in credentials for Jira real mode"
            )

        # Support Basic Auth or Bearer Token
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        if credentials.get("token"):
            headers["Authorization"] = f"Bearer {credentials['token']}"
        elif credentials.get("username") and credentials.get("password"):
            import base64

            auth_str = f"{credentials['username']}:{credentials['password']}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_auth}"
        else:
            raise ValueError("Either token or username/password is required for Jira real mode")

        client = ConnectorHTTPClient(
            base_url=base_url,
            tenant_id=tenant_id,
            connector_name=self.connector_name,
            rate_limit_policy=self.rate_limit_policy,
            headers=headers,
        )

        if action == "search_issues":
            jql = params.get("jql")
            if not jql:
                raise ValueError("jql is required for search_issues")
            return await client.request("GET", "/rest/api/3/search", params={"jql": jql})

        elif action == "get_issue":
            issue_key = params.get("issue_key")
            if not issue_key:
                raise ValueError("issue_key is required for get_issue")
            return await client.request("GET", f"/rest/api/3/issue/{issue_key}")

        elif action in ["add_comment", "create_issue"]:
            # High-risk write path
            approval_kwargs = kwargs.copy()
            approval_kwargs.pop("tenant_id", None)
            await self._ensure_approval(tenant_id, action, self.risk_level, **approval_kwargs)
            idempotency_key = kwargs.get("idempotency_key") or invocation_id

            if action == "add_comment":
                issue_key = params.get("issue_key")
                body = params.get("body")
                if not issue_key or not body:
                    raise ValueError("issue_key and body are required for add_comment")
                # Minimal Jira v3 comment format
                payload = {
                    "body": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {"type": "paragraph", "content": [{"text": body, "type": "text"}]}
                        ],
                    }
                }
                result = await client.request(
                    "POST",
                    f"/rest/api/3/issue/{issue_key}/comment",
                    json_data=payload,
                    idempotency_key=idempotency_key,
                )
            else:  # create_issue
                project_key = params.get("project_key")
                summary = params.get("summary")
                if not project_key or not summary:
                    raise ValueError("project_key and summary are required for create_issue")
                payload = {
                    "fields": {
                        "project": {"key": project_key},
                        "summary": summary,
                        "issuetype": {"name": params.get("issue_type", "Task")},
                    }
                }
                if params.get("description"):
                    payload["fields"]["description"] = {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"text": params["description"], "type": "text"}],
                            }
                        ],
                    }
                result = await client.request(
                    "POST", "/rest/api/3/issue", json_data=payload, idempotency_key=idempotency_key
                )

            await self._register_receipt(tenant_id, result, invocation_id)
            return result

        raise self._unsupported_action(
            action,
            mode="real",
            supported_actions=["add_comment", "create_issue", "get_issue", "search_issues"],
        )

    async def _execute_mock(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        if action == "search_issues":
            return self._with_execution_metadata(
                {"issues": [{"key": "PROJ-1", "summary": "Fix login bug"}]},
                mode="mock",
            )
        elif action == "get_issue":
            return self._with_execution_metadata(
                {
                    "issue": {
                        "key": params.get("issue_key"),
                        "summary": "Mock Issue",
                        "status": "To Do",
                    }
                },
                mode="mock",
            )
        elif action == "add_comment":
            return self._with_execution_metadata(
                {"status": "success", "comment_id": "10001"},
                mode="mock",
            )
        elif action == "create_issue":
            return self._with_execution_metadata(
                {"status": "success", "issue_key": "PROJ-123"},
                mode="mock",
            )

        raise self._unsupported_action(
            action,
            mode="mock",
            supported_actions=["add_comment", "create_issue", "get_issue", "search_issues"],
        )
