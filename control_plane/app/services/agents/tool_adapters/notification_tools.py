from typing import Any

from app.services.agents.tool_adapter_contract import ToolAdapterContract
from app.services.notifications.notification_router import NotificationRouterService


class NotifyEmailToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "notify_email"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "recipient": {"type": "string", "description": "Email address of the recipient."},
                "title": {"type": "string", "description": "Subject of the email."},
                "body": {"type": "string", "description": "Body of the email."},
            },
            "required": ["recipient", "title", "body"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "event_id": {"type": "string"},
                "audit_hash": {"type": "string"},
                "error": {"type": "string"},
            },
        }

    @property
    def side_effect_level(self) -> str:
        return "external"

    async def execute(self, **kwargs) -> dict[str, Any]:
        db = kwargs.get("db")
        if not db:
            raise ValueError("Database session is required to execute notification tool.")

        tenant_id = kwargs.get("tenant_id", "default")
        run_id = kwargs.get("run_id")
        run_id_str = str(run_id) if run_id else None

        recipient = kwargs.get("recipient")
        title = kwargs.get("title")
        body = kwargs.get("body")

        res = await NotificationRouterService.dispatch(
            db=db,
            tenant_id=tenant_id,
            channel="email",
            recipient=recipient,
            title=title,
            body=body,
            run_id=run_id_str,
        )
        return res

    async def dry_run(self, **kwargs) -> dict[str, Any]:
        return {"status": "skipped", "message": "Dry run of notify_email tool."}

    async def rollback(self, invocation_id: str, **kwargs) -> dict[str, Any]:
        return {"status": "success", "message": "No rollback possible for sent emails."}

    async def healthcheck(self) -> bool:
        return True


class NotifyPushToolAdapter(ToolAdapterContract):
    @property
    def name(self) -> str:
        return "notify_push"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User ID of the recipient push devices.",
                },
                "title": {"type": "string", "description": "Title of the push notification."},
                "body": {"type": "string", "description": "Body of the push notification."},
            },
            "required": ["user_id", "title", "body"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "event_id": {"type": "string"},
                "audit_hash": {"type": "string"},
                "error": {"type": "string"},
            },
        }

    @property
    def side_effect_level(self) -> str:
        return "external"

    async def execute(self, **kwargs) -> dict[str, Any]:
        db = kwargs.get("db")
        if not db:
            raise ValueError("Database session is required to execute notification tool.")

        tenant_id = kwargs.get("tenant_id", "default")
        run_id = kwargs.get("run_id")
        run_id_str = str(run_id) if run_id else None

        user_id = kwargs.get("user_id")
        title = kwargs.get("title")
        body = kwargs.get("body")

        res = await NotificationRouterService.dispatch(
            db=db,
            tenant_id=tenant_id,
            channel="push",
            recipient=user_id,
            title=title,
            body=body,
            run_id=run_id_str,
        )
        return res

    async def dry_run(self, **kwargs) -> dict[str, Any]:
        return {"status": "skipped", "message": "Dry run of notify_push tool."}

    async def rollback(self, invocation_id: str, **kwargs) -> dict[str, Any]:
        return {"status": "success", "message": "No rollback possible for sent pushes."}

    async def healthcheck(self) -> bool:
        return True
