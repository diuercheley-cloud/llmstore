# Owner: agent-platform
import uuid
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.agents import AgentApprovalRequest
from app.core.time import utc_now

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
        # Logic to find requests near expires_at and update escalated_to_role
        pass

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
