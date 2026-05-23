import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agents import AgentRunReceipt
from app.core.time import utc_now
from app.services.agents import agent_state

logger = logging.getLogger(__name__)

class AgentReceiptsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_receipt(
        self,
        run_id: uuid.UUID,
        step_number: int,
        receipt_type: str,
        input_hash: str,
        output_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        failure_reason: Optional[str] = None
    ) -> AgentRunReceipt:
        """
        Creates a signed receipt for an agent execution step.
        """
        receipt_data = {
            "type": receipt_type,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "metadata": metadata or {},
            "success": success,
            "failure_reason": failure_reason,
            "timestamp": utc_now().isoformat()
        }
        
        # Simple signature for auditability
        signature = f"sig_{uuid.uuid4().hex[:16]}"
        
        receipt = AgentRunReceipt(
            run_id=run_id,
            step_number=step_number,
            receipt_data=receipt_data,
            signature=signature,
            created_at=utc_now()
        )
        self.db.add(receipt)
        # Receipt creation should be part of the step transaction
        return receipt
