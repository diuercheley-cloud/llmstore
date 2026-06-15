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


class Microsoft365Connector(ConnectorAdapter):
    @property
    def connector_name(self) -> str:
        return "microsoft365"

    @property
    def mode(self) -> ConnectorMode:
        return ConnectorRuntime.get_mode(self.connector_name)

    @property
    def connector_version(self) -> str:
        return "1.1.0"

    @property
    def provider(self) -> str:
        return "Microsoft"

    @property
    def capabilities(self) -> list[ConnectorCapability]:
        return [ConnectorCapability.SEARCH, ConnectorCapability.READ, ConnectorCapability.CREATE]

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "search_mail_metadata",
                        "get_calendar_events_metadata",
                        "create_calendar_draft",
                    ],
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
        return ["Mail.Read", "Calendars.ReadWrite"]

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.HIGH

    @property
    def side_effect_level(self) -> SideEffectLevel:
        return SideEffectLevel.EXTERNAL

    @property
    def rate_limit_policy(self) -> dict[str, Any]:
        return {"requests_per_minute": 200}

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
            "search_mail_metadata": ConnectorCapability.SEARCH,
            "get_calendar_events_metadata": ConnectorCapability.READ,
            "create_calendar_draft": ConnectorCapability.CREATE,
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

        token = credentials.get("token") or credentials.get("api_key")
        if not token:
            raise ValueError("token is required for Microsoft 365 real mode")

        client = ConnectorHTTPClient(
            base_url="https://graph.microsoft.com/v1.0",
            tenant_id=tenant_id,
            connector_name=self.connector_name,
            rate_limit_policy=self.rate_limit_policy,
            headers={"Authorization": f"Bearer {token}"},
        )

        if action == "search_mail_metadata":
            q = params.get("q", "")
            return await client.request("GET", "/me/messages", params={"$search": f'"{q}"'})
        elif action == "get_calendar_events_metadata":
            return await client.request("GET", "/me/events")
        elif action == "create_calendar_draft":
            # High-risk write path
            approval_kwargs = kwargs.copy()
            approval_kwargs.pop("tenant_id", None)
            await self._ensure_approval(tenant_id, action, self.risk_level, **approval_kwargs)
            idempotency_key = kwargs.get("idempotency_key") or invocation_id

            subject = params.get("subject")
            start = params.get("start")
            end = params.get("end")
            if not subject or not start or not end:
                raise ValueError("subject, start, and end are required for create_calendar_draft")
            payload = {
                "subject": subject,
                "start": {"dateTime": start, "timeZone": params.get("time_zone", "UTC")},
                "end": {"dateTime": end, "timeZone": params.get("time_zone", "UTC")},
                "body": {
                    "contentType": "text",
                    "content": params.get("body", ""),
                },
            }
            result = await client.request(
                "POST", "/me/events", json_data=payload, idempotency_key=idempotency_key
            )

            await self._register_receipt(tenant_id, result, invocation_id)
            return result

        raise self._unsupported_action(
            action,
            mode="real",
            supported_actions=[
                "create_calendar_draft",
                "get_calendar_events_metadata",
                "search_mail_metadata",
            ],
        )

    async def _execute_mock(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        if action == "search_mail_metadata":
            return self._with_execution_metadata(
                {"emails": [{"subject": "Welcome", "from": "support@microsoft.com"}]},
                mode="mock",
            )
        elif action == "get_calendar_events_metadata":
            return self._with_execution_metadata(
                {"events": [{"subject": "Sprint Planning", "start": "2026-05-22T10:00:00Z"}]},
                mode="mock",
            )
        elif action == "create_calendar_draft":
            return self._with_execution_metadata(
                {"status": "success", "event_id": "EVT999"},
                mode="mock",
            )

        raise self._unsupported_action(
            action,
            mode="mock",
            supported_actions=[
                "create_calendar_draft",
                "get_calendar_events_metadata",
                "search_mail_metadata",
            ],
        )
