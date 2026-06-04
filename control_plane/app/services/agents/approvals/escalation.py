# Owner: agent-platform
import logging
import uuid

from app.core.time import utc_now
from app.models.agents import AgentApprovalRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class EscalationService:
    """
    Handles escalation paths for HITL requests.
    Paths: timeout, high risk, missing reviewer.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def escalate_on_timeout(self):
        """
        Escalates pending requests that are close to expiration.
        """
        from datetime import timedelta

        now = utc_now()
        stmt = select(AgentApprovalRequest).where(
            AgentApprovalRequest.status == "pending",
            AgentApprovalRequest.escalation_status == "none",
            AgentApprovalRequest.expires_at <= now + timedelta(minutes=5),
            AgentApprovalRequest.expires_at > now,
        )
        res = await self.db.execute(stmt)
        near_expiry = res.scalars().all()

        for req in near_expiry:
            days_until_expiry = (req.expires_at - now).days
            if days_until_expiry <= 0:
                await self.escalate_request(req.id, "admin_write", "Request near expiration")
            else:
                await self.escalate_request(req.id, "super_admin", "Request expiration imminent")

        expired_stmt = select(AgentApprovalRequest).where(
            AgentApprovalRequest.status.in_(["pending"]),
            AgentApprovalRequest.expires_at <= now,
        )
        res2 = await self.db.execute(expired_stmt)
        expired = res2.scalars().all()

        for req in expired:
            req.status = "expired"
            if req.escalation_status == "none":
                req.escalation_status = "escalated"
                req.escalated_to_role = "super_admin"
                req.reason = f"{req.reason} | ESCALATED: Request expired, auto-escalated"
            logger.info(f"Request {req.id} expired and auto-escalated")

    async def escalate_request(self, request_id: uuid.UUID, to_role: str, reason: str):
        stmt = select(AgentApprovalRequest).where(AgentApprovalRequest.id == request_id)
        res = await self.db.execute(stmt)
        req = res.scalar_one_or_none()
        
        if req and req.status == "pending":
            req.escalation_status = "escalated"
            req.escalated_to_role = to_role
            req.reason = f"{req.reason} | ESCALATED: {reason}"
            await self.db.flush()
            logger.info(f"Request {request_id} escalated to {to_role}")

    async def auto_escalate_high_risk(self):
        """
        Automatically escalates critical risk requests to super_admin.
        """
        stmt = select(AgentApprovalRequest).where(
            AgentApprovalRequest.status == "pending",
            AgentApprovalRequest.risk_level == "critical",
            AgentApprovalRequest.escalation_status == "none"
        )
        res = await self.db.execute(stmt)
        reqs = res.scalars().all()
        
        for req in reqs:
            await self.escalate_request(req.id, "super_admin", "Critical risk auto-escalation")
