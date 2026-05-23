# Owner: Platform Operations
from typing import Any, Dict, List
from app.services.agents.connectors.base import ConnectorAdapter, ConnectorCapability, RiskLevel, SideEffectLevel

class Microsoft365Connector(ConnectorAdapter):
    @property
    def connector_name(self) -> str:
        return "microsoft365"

    @property
    def connector_version(self) -> str:
        return "1.0.0"

    @property
    def provider(self) -> str:
        return "Microsoft"

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
                "action": {"type": "string", "enum": ["search_mail_metadata", "get_calendar_events_metadata", "create_calendar_draft"]},
                "params": {"type": "object"}
            },
            "required": ["action"]
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    @property
    def required_scopes(self) -> List[str]:
        return ["Mail.Read", "Calendars.ReadWrite"]

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.HIGH

    @property
    def side_effect_level(self) -> SideEffectLevel:
        return SideEffectLevel.EXTERNAL

    @property
    def rate_limit_policy(self) -> Dict[str, Any]:
        return {"requests_per_minute": 200}

    async def healthcheck(self) -> bool:
        return True

    async def dry_run(self, tenant_id: str, credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        return {"status": "dry_run_success", "connector": self.connector_name, "action": kwargs.get("action")}

    async def execute(self, tenant_id: str, credentials: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        action = kwargs.get("action")
        params = kwargs.get("params", {})
        
        capability_map = {
            "search_mail_metadata": ConnectorCapability.SEARCH,
            "get_calendar_events_metadata": ConnectorCapability.READ,
            "create_calendar_draft": ConnectorCapability.CREATE
        }
        
        capability = capability_map.get(action)
        if not capability:
            raise ValueError(f"Unknown action: {action}")
        
        self._check_feature_flags(capability)

        if action == "search_mail_metadata":
            return {"emails": [{"subject": "Welcome", "from": "support@microsoft.com"}]}
        elif action == "get_calendar_events_metadata":
            return {"events": [{"subject": "Sprint Planning", "start": "2026-05-22T10:00:00Z"}]}
        elif action == "create_calendar_draft":
            return {"status": "success", "event_id": "EVT999"}
            
        return {"status": "error", "message": "Action not implemented"}
