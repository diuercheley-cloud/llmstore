# Owner: agent-platform
import asyncio
import logging
import uuid
from typing import Any, Dict

from app.services.agents import agent_runtime
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class SyncInvocationService:
    """
    Handles synchronous agent invocations with timeouts.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def invoke_sync(self, agent_id: uuid.UUID, tenant_id: str, input_text: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Starts a run and waits for completion or timeout.
        """
        run = await agent_runtime.start_run(self.db, agent_id, tenant_id, input_text)
        
        start_time = asyncio.get_event_loop().time()
        while True:
            await self.db.refresh(run)
            if run.status in ("completed", "failed", "cancelled"):
                return {
                    "run_id": str(run.id),
                    "status": run.status,
                    "output": run.context.get("final_response"), # Simplified
                    "error": run.failure_reason
                }
                
            if (asyncio.get_event_loop().time() - start_time) > timeout:
                logger.warning(f"Sync invocation timeout for run {run.id}")
                return {
                    "run_id": str(run.id),
                    "status": "timeout",
                    "message": f"Execution exceeded sync timeout of {timeout}s. Checking status via GET /runs/{run.id} is recommended."
                }
            
            await asyncio.sleep(1)
