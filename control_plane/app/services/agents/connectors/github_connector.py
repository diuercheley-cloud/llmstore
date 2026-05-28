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

class GitHubConnector(ConnectorAdapter):
    def __init__(self):
        self.base_url = "https://api.github.com"

    @property
    def connector_name(self) -> str:
        return "github"

    @property
    def mode(self) -> ConnectorMode:
        return ConnectorRuntime.get_mode(self.connector_name)

    @property
    def connector_version(self) -> str:
        return "1.1.0"

    @property
    def provider(self) -> str:
        return "GitHub"

    @property
    def capabilities(self) -> List[ConnectorCapability]:
        return [
            ConnectorCapability.SEARCH,
            ConnectorCapability.READ,
            ConnectorCapability.COMMENT,
            ConnectorCapability.CREATE
        ]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["search_repositories", "get_issue", "create_issue_comment", "create_issue", "list_issues"]},
                "params": {"type": "object"}
            },
            "required": ["action"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    @property
    def required_scopes(self) -> List[str]:
        return ["repo", "user"]

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    @property
    def side_effect_level(self) -> SideEffectLevel:
        return SideEffectLevel.EXTERNAL

    @property
    def rate_limit_policy(self) -> Dict[str, Any]:
        return {"requests_per_minute": 5000}

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
        
        # 1. Governance check (Feature Flags)
        capability_map = {
            "search_repositories": ConnectorCapability.SEARCH,
            "get_issue": ConnectorCapability.READ,
            "list_issues": ConnectorCapability.READ,
            "create_issue_comment": ConnectorCapability.COMMENT,
            "create_issue": ConnectorCapability.CREATE
        }
        
        capability = capability_map.get(action)
        if not capability:
            raise ValueError(f"Unknown action: {action}")
        
        self._check_feature_flags(capability)

        # Agent IAM Check
        await self.check_iam(tenant_id, credentials, action)

        # Audit event
        await self.audit_connector_call(tenant_id, credentials, action, {"params": params, "mode": self.mode})

        # Mode-based execution
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
            base_url=self.base_url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Agentic-AI-Platform"
            }
        )

        if action == "list_issues":
            owner = params.get("owner")
            repo = params.get("repo")
            if not owner or not repo:
                raise ValueError("owner and repo are required for list_issues")
            return await client.request("GET", f"/repos/{owner}/{repo}/issues")

        elif action == "get_issue":
            owner = params.get("owner")
            repo = params.get("repo")
            issue_number = params.get("issue_number")
            if not owner or not repo or not issue_number:
                raise ValueError("owner, repo, and issue_number are required for get_issue")
            return await client.request("GET", f"/repos/{owner}/{repo}/issues/{issue_number}")

        elif action == "create_issue_comment":
            owner = params.get("owner")
            repo = params.get("repo")
            issue_number = params.get("issue_number")
            body = params.get("body")
            if not owner or not repo or not issue_number or not body:
                raise ValueError("owner, repo, issue_number, and body are required for create_issue_comment")
            
            # Additional write guard if not already handled by _check_feature_flags
            return await client.request("POST", f"/repos/{owner}/{repo}/issues/{issue_number}/comments", json_data={"body": body})

        elif action == "search_repositories":
            q = params.get("q")
            if not q:
                raise ValueError("query 'q' is required for search_repositories")
            return await client.request("GET", "/search/repositories", params={"q": q})

        elif action == "create_issue":
            owner = params.get("owner")
            repo = params.get("repo")
            title = params.get("title")
            if not owner or not repo or not title:
                raise ValueError("owner, repo, and title are required for create_issue")
            payload = {"title": title}
            if params.get("body"):
                payload["body"] = params["body"]
            return await client.request("POST", f"/repos/{owner}/{repo}/issues", json_data=payload)

        raise self._unsupported_action(
            action,
            mode="real",
            supported_actions=["create_issue", "create_issue_comment", "get_issue", "list_issues", "search_repositories"],
        )

    async def _execute_mock(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "search_repositories":
            return self._with_execution_metadata(
                {"repositories": [{"name": "repo1", "url": "https://github.com/org/repo1"}]},
                mode="mock",
            )
        elif action == "get_issue":
            return self._with_execution_metadata(
                {"issue": {"id": params.get("issue_id"), "title": "Mock Issue", "state": "open"}},
                mode="mock",
            )
        elif action == "list_issues":
            return self._with_execution_metadata(
                {"issues": [{"id": 1, "title": "Mock Issue 1"}, {"id": 2, "title": "Mock Issue 2"}]},
                mode="mock",
            )
        elif action == "create_issue_comment":
            return self._with_execution_metadata(
                {"status": "success", "comment_id": "mock_comment_123"},
                mode="mock",
            )
        elif action == "create_issue":
            return self._with_execution_metadata(
                {"status": "success", "issue_id": "mock_issue_456"},
                mode="mock",
            )
            
        raise self._unsupported_action(
            action,
            mode="mock",
            supported_actions=["create_issue", "create_issue_comment", "get_issue", "list_issues", "search_repositories"],
        )
