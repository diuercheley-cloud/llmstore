import logging
import uuid
from typing import Any

from app.models.agents.agent_notifications import NotificationEvent
from app.services.notifications.email_provider import EmailProviderService
from app.services.notifications.notification_audit import NotificationAuditService
from app.services.notifications.notification_policy import NotificationPolicyService
from app.services.notifications.push_provider import PushProviderService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("notification_router")


class NotificationRouterService:
    @classmethod
    async def dispatch(
        cls,
        db: AsyncSession,
        tenant_id: str,
        channel: str,  # "email" or "push"
        recipient: str,  # email string or user_id string
        title: str,
        body: str,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrates policy checks, dispatches to providers,
        logs database events, and writes audit trails.
        """
        # Convert run_id to UUID if provided and valid
        run_uuid = None
        if run_id:
            try:
                run_uuid = uuid.UUID(run_id)
            except ValueError:
                pass

        # 1. Create a pending event record
        event = NotificationEvent(
            tenant_id=tenant_id,
            run_id=run_uuid,
            channel=channel,
            recipient=recipient,
            title=title,
            body=body,
            status="pending",
        )
        db.add(event)
        await db.flush()

        try:
            # 2. Evaluate policy
            await NotificationPolicyService.evaluate_policy(
                db=db,
                tenant_id=tenant_id,
                run_id=run_id,
                title=title,
                body=body,
                recipient=recipient,
                channel=channel,
            )
        except ValueError as e:
            err_msg = str(e)
            status = "policy_blocked"
            if "rate limit" in err_msg.lower():
                status = "rate_limited"

            event.status = status
            event.failure_reason = err_msg

            # Generate failure receipt
            audit = NotificationAuditService.generate_receipt(
                tenant_id=tenant_id,
                run_id=run_id,
                channel=channel,
                recipient=recipient,
                title=title,
                body=body,
                status=status,
                additional_info={"error": err_msg},
            )
            event.audit_hash = audit["audit_hash"]
            await db.commit()

            logger.warning(f"Notification blocked by policy: {err_msg}")
            return {
                "status": status,
                "error": err_msg,
                "event_id": str(event.id),
                "audit_hash": audit["audit_hash"],
            }

        # 3. Dispatch to provider
        try:
            if channel == "email":
                res = await EmailProviderService.send_email(
                    db=db, tenant_id=tenant_id, recipient=recipient, title=title, body=body
                )
            elif channel == "push":
                res = await PushProviderService.send_push(
                    db=db, tenant_id=tenant_id, user_id=recipient, title=title, body=body
                )
            else:
                raise ValueError(f"Unsupported notification channel: {channel}")

            event.status = "sent"
            audit = NotificationAuditService.generate_receipt(
                tenant_id=tenant_id,
                run_id=run_id,
                channel=channel,
                recipient=recipient,
                title=title,
                body=body,
                status="sent",
                additional_info={"provider_response": res},
            )
            event.audit_hash = audit["audit_hash"]
            await db.commit()

            return {
                "status": "sent",
                "event_id": str(event.id),
                "audit_hash": audit["audit_hash"],
                "details": res,
            }

        except Exception as e:
            err_msg = str(e)
            event.status = "failed"
            event.failure_reason = err_msg

            audit = NotificationAuditService.generate_receipt(
                tenant_id=tenant_id,
                run_id=run_id,
                channel=channel,
                recipient=recipient,
                title=title,
                body=body,
                status="failed",
                additional_info={"error": err_msg},
            )
            event.audit_hash = audit["audit_hash"]
            await db.commit()

            logger.error(f"Notification dispatch failed: {err_msg}")
            return {
                "status": "failed",
                "error": err_msg,
                "event_id": str(event.id),
                "audit_hash": audit["audit_hash"],
            }
