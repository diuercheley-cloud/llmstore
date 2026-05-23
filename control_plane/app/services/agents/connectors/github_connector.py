# Owner: Platform Operations
from typing import Any, Dict, List
from app.services.agents.connectors.base import ConnectorAdapter, ConnectorCapability, RiskLevel, SideEffectLevel

class GitHubConnector(ConnectorAdapter):
    @property
    def connector_name(self) -> str:
        return "github"

    @property
    def connector_version(self) -> str:
        return "1.0.0"

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
                "action": {"type": "string", "enum": ["search_repositories", "get_issue", "create_issue_comment", "create_issue"]},
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
        return {"status": "dry_run_success", "connector": self.connector_name, "action": kwargs.get("action")}

    async def execute(self, tenant_id: str, credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action")
        params = kwargs.get("params", {})
        
        # 1. Governance check (Feature Flags)
        capability_map = {
            "search_repositories": ConnectorCapability.SEARCH,
            "get_issue": ConnectorCapability.READ,
            "create_issue_comment": ConnectorCapability.COMMENT,
            "create_issue": ConnectorCapability.CREATE
        }
        
        capability = capability_map.get(action)
        if not capability:
            raise ValueError(f"Unknown action: {action}")
        
        self._check_feature_flags(capability)

        # 2. Scope check
        from app.services.agents.connectors.connector_scopes import ConnectorScopeManager
        from app.db.session import SessionLocal
        async with SessionLocal() as db:
            scope_manager = ConnectorScopeManager(db)
            provided_scopes = credentials.get("scopes", [])
            if not await scope_manager.check_scopes(tenant_id, self.connector_name, action, provided_scopes):
                 raise PermissionError(f"Insufficient scope for action '{action}' on {self.connector_name}")

        # 3. Mock implementation
        if action == "search_repositories":
            return {"repositories": [{"name": "repo1", "url": "https://github.com/org/repo1"}]}
        elif action == "get_issue":
            return {"issue": {"id": params.get("issue_id"), "title": "Mock Issue", "state": "open"}}
        elif action == "create_issue_comment":
            return {"status": "success", "comment_id": "mock_comment_123"}
        elif action == "create_issue":
            return {"status": "success", "issue_id": "mock_issue_456"}
            
        return {"status": "error", "message": "Action not implemented"}
