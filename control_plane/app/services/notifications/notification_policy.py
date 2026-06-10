import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.agents.agent_notifications import NotificationEvent
from app.models.agents.agents import AgentApprovalRequest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("notification_policy")

SENSITIVE_KEYWORDS = ["delete", "destroy", "payment", "critical", "transfer"]

# Regex patterns for scanning sensitive credentials and secrets
SECRET_PATTERNS = [
    r"(?i)(password|passwd|pwd|secret|api_key|apikey|token|private_key|auth_token)\s*[:=]\s*[a-zA-Z0-9_\-\.\~]{8,}",
    r"-----BEGIN[ A-Z0-9_]*PRIVATE KEY-----",
    r"aws_access_key_id\s*[:=]\s*[A-Z0-9]{20}",
    r"aws_secret_access_key\s*[:=]\s*[a-zA-Z0-9/+=]{40}"
]


def has_sensitive_keywords(title: str, body: str) -> bool:
    """Returns True if the content contains any of the defined sensitive keywords."""
    content = f"{title} {body}".lower()
    return any(kw in content for kw in SENSITIVE_KEYWORDS)


def contains_secrets(title: str, body: str) -> bool:
    """Returns True if the content matches any of the secret detection patterns."""
    content = f"{title}\n{body}"
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, content):
            return True
    return False


class NotificationPolicyService:
    @classmethod
    async def evaluate_policy(
        cls,
        db: AsyncSession,
        tenant_id: str,
        run_id: Optional[str],
        title: str,
        body: str,
        recipient: str,
        channel: str
    ) -> None:
        """
        Evaluates policies for email/push notification.
        Raises ValueError if any policy is violated.
        """
        # 1. No secrets rule
        if contains_secrets(title, body):
            raise ValueError("Access denied: message contains sensitive secrets or credentials.")

        # 2. Rate limit rule (default 5 messages per 60 seconds per tenant)
        window = datetime.now(timezone.utc) - timedelta(seconds=60)
        stmt = select(func.count(NotificationEvent.id)).where(
            NotificationEvent.tenant_id == tenant_id,
            NotificationEvent.created_at >= window
        )
        res = await db.execute(stmt)
        count = res.scalar() or 0
        if count >= 5:
            raise ValueError("Rate limit exceeded: maximum of 5 notifications per minute.")

        # 3. Approval for sensitive messages rule
        if has_sensitive_keywords(title, body):
            if not run_id:
                raise ValueError("Approval required for sensitive notification content, but no agent run context provided.")

            # Check if there is an approved AgentApprovalRequest for this run
            # where the status is 'approved'
            import uuid
            stmt_approval = select(AgentApprovalRequest).where(
                AgentApprovalRequest.agent_run_id == uuid.UUID(run_id),
                AgentApprovalRequest.status == "approved"
            )
            res_approval = await db.execute(stmt_approval)
            approvals = res_approval.scalars().all()

            # Verify if any of the approved requests correspond to the notification tool call
            approved = False
            for app in approvals:
                context = app.sanitized_context or {}
                tool_name = context.get("tool_name")
                if tool_name in ("notify_email", "notify_push"):
                    # Match input recipient / title / body
                    raw_input = app.raw_tool_input or {}
                    if (
                        raw_input.get("recipient") == recipient or
                        raw_input.get("user_id") == recipient
                    ):
                        approved = True
                        break

            if not approved:
                raise ValueError("Approval required: message contains sensitive keywords and has not been approved.")
