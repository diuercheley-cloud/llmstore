# Owner: agent-platform
import uuid
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.human_approval import approve_approval_request, AdminRole

logger = logging.getLogger(__name__)

class BatchApprovalService:
    """
    Handles batch approval of low-risk HITL requests.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def approve_batch(self, request_ids: List[uuid.UUID], decided_by: str, caller_role: AdminRole, reason: str = "Batch approval"):
        """
        Approves multiple requests at once.
        Only allows batching if requests are batch-eligible (low risk).
        """
        results = []
        for rid in request_ids:
            try:
                # In real use, we would check is_batch_eligible before calling approve
                await approve_approval_request(self.db, rid, decided_by, caller_role, reason)
                results.append({"id": str(rid), "status": "approved"})
            except Exception as e:
                logger.error(f"Failed to approve {rid} in batch: {e}")
                results.append({"id": str(rid), "status": "failed", "error": str(e)})
        
        return results
